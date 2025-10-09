from copy import deepcopy
import logging
from datathread import DataThread
from PyQt5.QtCore import Qt, QPointF, QPoint, QLine, QLineF
from PyQt5.QtGui import QPalette, QPainter, QPen
from PyQt5.QtWidgets import QWidget
import math

CHANNEL_Y_FILL = 0.7  # How much of the per-channel vertical space is filled.  > 1 will overlap the lines.
import pyqtgraph as pg

logger = logging.getLogger("phohale.sigvisualizer.MultiStreamPlotManagingWidget")

# class MultiStreamPlotManagingWidget(pg.GraphicsLayoutWidget):
class MultiStreamPlotManagingWidget(pg.GraphicsLayoutWidget):
    """ the container widget that manages the plots for multiple LSL streams, each of which can have multiple channels """

    def __init__(self, widget):
        super().__init__()
        self.reset()
        self.stream_plots = {} ## a dictionary of stream name to plot widget
        self.stream_plot_channels = {} ## a dictionary of stream name to a dictionary of channel name to channel widget

        self.dataTr = DataThread(self)
        self.dataTr.sendData.connect(self.get_data)
        self.dataTr.changedStream.connect(self.reset)
        self.last_x_range = None
        logger.info(f'MultiStreamPlotManagingWidget initialized')


    def reset(self):
        logger.info(f'MultiStreamPlotManagingWidget reset')
        for k, v in self.stream_plots.items():
            self.removeItem(v)
            v.deleteLater()
        self.stream_plots.clear()
        self.stream_plot_channels.clear()
        self.clear()
        self.last_x_range = None
        # self.update()
        # self.repaint()


    def on_streams_updated(self, metadata, default_idx):
        """ called when the streams are changed (new streams/etc)
        1. Need to update the tree widget with the new streams and channels 
        2. Update the plotted graphs (building new ones/removing old ones if needed) so they can be displayed when updated date is received.

        TODO 2025-10-09 - moving away from single stream selection (specified by default_idx) to being able to preview multiple streams simultaneously.


        # p1 = self.addPlot(row=0, col=0)
        # p2 = self.addPlot(row=0, col=1)
        # v = self.addViewBox(row=1, col=0, colspan=2)
        #         
        """
        logger.info(f'MultiStreamPlotManagingWidget on_streams_updated() started.')
        self.reset()

        for s_ix, s_meta in enumerate(metadata):
            a_stream_name: str = s_meta["name"]
            a_plot_item = self.addPlot(row=s_ix, col=0)
            self.stream_plots[a_stream_name] = a_plot_item
            self.stream_plot_channels[a_stream_name] = {} ## initialize to new

            a_plot_item.setBackground('w')
            a_plot_item.showGrid(x=True, y=True, alpha=0.3)
            # a_plot_item.setMouseEnabled(x=False, y=False)
            a_plot_item.hideButtons()
            a_plot_item.setMenuEnabled(False)
            a_plot_item.setMouseEnabled(x=False, y=False)
            a_plot_item.setClipToView(True)
            a_plot_item.setDownsampling(mode='peak')
            a_plot_item.setAutoPan(y=False)
            a_plot_item.setAutoVisible(y=True)
            a_plot_item.setLabel('bottom', 'Time', units='s')
            a_plot_item.setLabel('left', a_stream_name)
            
            ## Setup channels for the plot
            for m in range(s_meta["ch_count"]):
                channel_name: str = s_meta["ch_labels"][m]
                if not channel_name:
                    channel_name = f'Ch[{m}]'
                self.stream_plot_channels[s_meta["name"]][channel_name] = {'name': channel_name, 'idx': m, 'tooltip': f'Channel[{m+1}]', 'is_enabled': True}
        ## END for s_ix, s_meta in enumerate(metadata)...
        logger.info(f'\tMultiStreamPlotManagingWidget on_streams_updated() finished.')


            



    def get_data(self, sig_ts, sig_buffer, marker_ts, marker_buffer):
        """ updates self.curves and self.marker_scatter 
        """
        logger.info(f'PaintWidget get_data(...) started.')

        # Defensive: check for valid buffer
        if not sig_buffer or not isinstance(sig_buffer, list) or not sig_buffer or not isinstance(sig_buffer[0], (list, tuple)):
            self.clear()
            self.curves = []
            self.n_channels = 0
            self.n_samples = 0
            return

        n_samples = len(sig_buffer)
        n_channels = len(sig_buffer[0]) if n_samples > 0 else 0
        self.n_channels = n_channels
        self.n_samples = n_samples

        # Defensive: check for valid timestamps
        if not sig_ts or len(sig_ts) != n_samples:
            x = list(range(n_samples))
            time_mode = False
        else:
            x = [t - sig_ts[0] for t in sig_ts]
            time_mode = True

        # Get channel labels if available
        if hasattr(self.dataTr, "stream_params") and self.dataTr.stream_params:
            try:
                ch_labels = self.dataTr.stream_params[self.dataTr.sig_strm_idx]['metadata'].get('ch_labels', [])
                if ch_labels and len(ch_labels) == n_channels:
                    self.channel_labels = ch_labels
            except Exception:
                self.channel_labels = []

        # Compute mean and scaling for each channel for robust display
        if not self.mean or len(self.mean) != n_channels:
            self.mean = [0 for _ in range(n_channels)]
        if not self.scaling or len(self.scaling) != n_channels:
            self.scaling = [1 for _ in range(n_channels)]

        # Calculate mean and scaling (robust: use median and IQR)
        for ch in range(n_channels):
            y = [row[ch] for row in sig_buffer]
            if y:
                median = sorted(y)[len(y)//2]
                iqr = (sorted(y)[int(0.75*len(y))] - sorted(y)[int(0.25*len(y))]) if len(y) > 3 else (max(y)-min(y) if max(y)!=min(y) else 1)
                self.mean[ch] = median
                self.scaling[ch] = iqr if iqr != 0 else 1

        # Remove old curves
        for c in self.curves:
            self.removeItem(c)
        self.curves = []

        # Plot each channel, offset vertically
        spacing = 1.0
        if n_channels > 0:
            spacing = CHANNEL_Y_FILL / max(n_channels, 1)
        y_offsets = [ch * spacing for ch in range(n_channels)]

        for ch in range(n_channels):
            y = [((row[ch] - self.mean[ch]) / self.scaling[ch] if self.scaling[ch] else row[ch]) + y_offsets[ch] for row in sig_buffer]
            pen = pg.mkPen(color=pg.intColor(ch, hues=n_channels, values=1, maxValue=200), width=1)
            curve = pg.PlotCurveItem(x, y, pen=pen, antialias=True)
            self.addItem(curve)
            self.curves.append(curve)

        # Set y-axis ticks to channel labels or numbers
        if self.channel_labels and len(self.channel_labels) == n_channels:
            yticks = [(y_offsets[ch], self.channel_labels[ch]) for ch in range(n_channels)]
        else:
            yticks = [(y_offsets[ch], str(ch+1)) for ch in range(n_channels)]
        ax = self.getPlotItem().getAxis('left')
        ax.setTicks([yticks])

        # Set x-axis range to fit the data
        if x:
            x_min, x_max = min(x), max(x)
            if x_min == x_max:
                x_max += 1
            self.setXRange(x_min, x_max, padding=0.01)
            self.last_x_range = (x_min, x_max)

        # Plot markers as scatter points
        if marker_ts and marker_buffer and n_channels > 0:
            marker_x = []
            marker_y = []
            for ts, ms in zip(marker_ts, marker_buffer):
                if time_mode:
                    x_val = ts - sig_ts[0]
                else:
                    # fallback: use sample index
                    try:
                        x_val = sig_ts.index(ts)
                    except Exception:
                        x_val = 0
                # Place marker at top of plot
                marker_x.append(x_val)
                marker_y.append(y_offsets[-1] + spacing*0.5)
            if self.marker_scatter:
                self.removeItem(self.marker_scatter)
            if marker_x:
                self.marker_scatter = pg.ScatterPlotItem(marker_x, marker_y, symbol='t', size=14, brush='r', pen=pg.mkPen('k', width=1))
                self.addItem(self.marker_scatter)
            else:
                self.marker_scatter = None
        elif self.marker_scatter:
            self.removeItem(self.marker_scatter)
            self.marker_scatter = None


        logger.info(f'PaintWidget repainting...')
        self.update()
        self.repaint()
        logger.info(f'PaintWidget get_data(...) finished.')
    

    def sizeHint(self):
        # Provide a reasonable default size
        return pg.QtCore.QSize(800, 400)


      



class PaintWidget(pg.PlotWidget):
    def __init__(self, widget):
        super().__init__()
        self.reset()
        self.setBackground('w')
        self.showGrid(x=True, y=True, alpha=0.3)
        self.dataTr = DataThread(self)
        self.dataTr.sendData.connect(self.get_data)
        self.dataTr.changedStream.connect(self.reset)
        self.curves = []
        self.marker_scatter = None
        self.n_channels = 0
        self.n_samples = 0
        self.setMouseEnabled(x=False, y=False)
        self.getPlotItem().hideButtons()
        self.getPlotItem().setMenuEnabled(False)
        self.getPlotItem().setMouseEnabled(x=False, y=False)
        self.getPlotItem().setClipToView(True)
        self.getPlotItem().setDownsampling(mode='peak')
        self.getPlotItem().setAutoPan(y=False)
        self.getPlotItem().setAutoVisible(y=True)
        self.getPlotItem().setLabel('bottom', 'Time', units='s')
        self.getPlotItem().setLabel('left', 'Channels')
        self.channel_labels = []
        self.last_x_range = None
        logger.info(f'PaintWidget initialized')


    def reset(self):
        logger.info(f'PaintWidget reset')
        self.chunk_idx = 0
        self.channelHeight = 0
        self.px_per_samp = 0
        self.dataBuffer = None
        self.markerBuffer = None
        self.lastY = []
        self.scaling = []
        self.mean = []
        self.t0 = 0
        self.n_channels = 0
        self.n_samples = 0
        self.channel_labels = []
        self.clear()
        self.curves = []
        self.marker_scatter = None
        self.last_x_range = None
        self.update()
        self.repaint()


    def get_data(self, sig_ts, sig_buffer, marker_ts, marker_buffer):
        """ updates self.curves and self.marker_scatter 
        """
        logger.info(f'PaintWidget get_data(...) started.')

        # Defensive: check for valid buffer
        if not sig_buffer or not isinstance(sig_buffer, list) or not sig_buffer or not isinstance(sig_buffer[0], (list, tuple)):
            self.clear()
            self.curves = []
            self.n_channels = 0
            self.n_samples = 0
            return

        n_samples = len(sig_buffer)
        n_channels = len(sig_buffer[0]) if n_samples > 0 else 0
        self.n_channels = n_channels
        self.n_samples = n_samples

        # Defensive: check for valid timestamps
        if not sig_ts or len(sig_ts) != n_samples:
            x = list(range(n_samples))
            time_mode = False
        else:
            x = [t - sig_ts[0] for t in sig_ts]
            time_mode = True

        # Get channel labels if available
        if hasattr(self.dataTr, "stream_params") and self.dataTr.stream_params:
            try:
                ch_labels = self.dataTr.stream_params[self.dataTr.sig_strm_idx]['metadata'].get('ch_labels', [])
                if ch_labels and len(ch_labels) == n_channels:
                    self.channel_labels = ch_labels
            except Exception:
                self.channel_labels = []

        # Compute mean and scaling for each channel for robust display
        if not self.mean or len(self.mean) != n_channels:
            self.mean = [0 for _ in range(n_channels)]
        if not self.scaling or len(self.scaling) != n_channels:
            self.scaling = [1 for _ in range(n_channels)]

        # Calculate mean and scaling (robust: use median and IQR)
        for ch in range(n_channels):
            y = [row[ch] for row in sig_buffer]
            if y:
                median = sorted(y)[len(y)//2]
                iqr = (sorted(y)[int(0.75*len(y))] - sorted(y)[int(0.25*len(y))]) if len(y) > 3 else (max(y)-min(y) if max(y)!=min(y) else 1)
                self.mean[ch] = median
                self.scaling[ch] = iqr if iqr != 0 else 1

        # Remove old curves
        for c in self.curves:
            self.removeItem(c)
        self.curves = []

        # Plot each channel, offset vertically
        spacing = 1.0
        if n_channels > 0:
            spacing = CHANNEL_Y_FILL / max(n_channels, 1)
        y_offsets = [ch * spacing for ch in range(n_channels)]

        for ch in range(n_channels):
            y = [((row[ch] - self.mean[ch]) / self.scaling[ch] if self.scaling[ch] else row[ch]) + y_offsets[ch] for row in sig_buffer]
            pen = pg.mkPen(color=pg.intColor(ch, hues=n_channels, values=1, maxValue=200), width=1)
            curve = pg.PlotCurveItem(x, y, pen=pen, antialias=True)
            self.addItem(curve)
            self.curves.append(curve)

        # Set y-axis ticks to channel labels or numbers
        if self.channel_labels and len(self.channel_labels) == n_channels:
            yticks = [(y_offsets[ch], self.channel_labels[ch]) for ch in range(n_channels)]
        else:
            yticks = [(y_offsets[ch], str(ch+1)) for ch in range(n_channels)]
        ax = self.getPlotItem().getAxis('left')
        ax.setTicks([yticks])

        # Set x-axis range to fit the data
        if x:
            x_min, x_max = min(x), max(x)
            if x_min == x_max:
                x_max += 1
            self.setXRange(x_min, x_max, padding=0.01)
            self.last_x_range = (x_min, x_max)

        # Plot markers as scatter points
        if marker_ts and marker_buffer and n_channels > 0:
            marker_x = []
            marker_y = []
            for ts, ms in zip(marker_ts, marker_buffer):
                if time_mode:
                    x_val = ts - sig_ts[0]
                else:
                    # fallback: use sample index
                    try:
                        x_val = sig_ts.index(ts)
                    except Exception:
                        x_val = 0
                # Place marker at top of plot
                marker_x.append(x_val)
                marker_y.append(y_offsets[-1] + spacing*0.5)
            if self.marker_scatter:
                self.removeItem(self.marker_scatter)
            if marker_x:
                self.marker_scatter = pg.ScatterPlotItem(marker_x, marker_y, symbol='t', size=14, brush='r', pen=pg.mkPen('k', width=1))
                self.addItem(self.marker_scatter)
            else:
                self.marker_scatter = None
        elif self.marker_scatter:
            self.removeItem(self.marker_scatter)
            self.marker_scatter = None


        logger.info(f'PaintWidget repainting...')
        self.update()
        self.repaint()
        logger.info(f'PaintWidget get_data(...) finished.')
    

    def sizeHint(self):
        # Provide a reasonable default size
        return pg.QtCore.QSize(800, 400)



    def paintEvent(self, event):
        # Delegate painting to PlotWidget so pyqtgraph items render correctly
        super().paintEvent(event)

        logger.info(f'PaintWidget paintEvent(...) finished.')

        
# class PaintWidget(QWidget):

#     def __init__(self, widget):
#         super().__init__()
#         self.reset()
#         pal = QPalette()
#         pal.setColor(QPalette.Background, Qt.white)
#         self.setAutoFillBackground(True)
#         self.setPalette(pal)

#         self.dataTr = DataThread(self)
#         self.dataTr.sendData.connect(self.get_data)
#         self.dataTr.changedStream.connect(self.reset)

#     def reset(self):
#         self.chunk_idx = 0
#         self.channelHeight = 0
#         self.px_per_samp = 0
#         self.dataBuffer = None
#         self.markerBuffer = None
#         self.lastY = []
#         self.scaling = []
#         self.mean = []
#         self.t0 = 0

#     def get_data(self, sig_ts, sig_buffer, marker_ts, marker_buffer):
#         update_x0 = float(self.width())
#         update_width = 0.

#         # buffer should have exactly self.dataTr.chunkSize samples or be empty
#         if any(sig_ts):
#             if not self.mean:
#                 self.mean = [0 for _ in range(len(sig_buffer[0]))]
#                 self.scaling = [1 for _ in range(len(sig_buffer[0]))]
#             if self.chunk_idx == 0:
#                 self.t0 = sig_ts[0]
#             self.dataBuffer = deepcopy(sig_buffer)
#             px_per_chunk = self.width() / self.dataTr.chunksPerScreen
#             update_x0 = self.chunk_idx * px_per_chunk
#             update_width = px_per_chunk

#         if any(marker_ts):
#             px_out = []
#             ms_out = []
#             px_per_sec = self.width() / self.dataTr.seconds_per_screen
#             for ts, ms in zip(marker_ts, marker_buffer):
#                 if any(sig_ts):  # Relative to signal timestamps
#                     this_px = update_x0 + (ts - sig_ts[0]) * px_per_sec
#                     if 0 <= this_px <= self.width():
#                         px_out.append(this_px)
#                         ms_out.append(','.join(ms))
#                 else:
#                     # TODO: Check samples vs pixels for both data stream and marker stream.
#                     # I think there is some rounding error.
                    
#                     if self.t0 <= ts <= (self.t0 + self.dataTr.seconds_per_screen):
#                         px_out.append((ts - self.t0) * px_per_sec)
#                         ms_out.append(','.join(ms))
#             if any(px_out):
#                 # Sometimes the marker might happen just off screen so we lose it.
#                 self.markerBuffer = zip(px_out, ms_out)
#                 update_x0 = min(update_x0, min(px_out))
#                 update_width = max(update_width, max([_ - update_x0 for _ in px_out]))

#         if any(sig_ts) and update_x0 == sig_ts[0]:
#             update_x0 -= self.px_per_samp  # Offset to connect with previous sample

#         # Repaint only the region of the screen containing this data chunk.
#         if update_width > 0:
#             self.update(int(update_x0), 0, int(update_width + 1), self.height())

#     def paintEvent(self, event):
#         painter = QPainter(self)
#         if self.dataBuffer is not None:
#             painter.setPen(QPen(Qt.blue))

#             n_samps = len(self.dataBuffer)
#             n_chans = len(self.dataBuffer[0])

#             self.channelHeight = self.height() / n_chans
#             self.px_per_samp = self.width() / self.dataTr.chunksPerScreen / n_samps

#             # ======================================================================================================
#             # Calculate Trend and Scaling
#             # ======================================================================================================
#             if self.chunk_idx == 0 or not self.mean:
#                 for chan_idx in range(n_chans):
#                     samps_for_chan = [frame[chan_idx] for frame in self.dataBuffer]
#                     self.mean[chan_idx] = sum(samps_for_chan) / len(samps_for_chan)

#                     for m in range(len(samps_for_chan)):
#                         samps_for_chan[m] -= self.mean[chan_idx]

#                     data_range = (max(samps_for_chan) - min(samps_for_chan) + 0.0000000000001)
#                     self.scaling[chan_idx] = self.channelHeight * CHANNEL_Y_FILL / data_range

#             # ======================================================================================================
#             # Trend Removal and Scaling
#             # ======================================================================================================
#             try:
#                 for samp_idx in range(n_samps):
#                     for chan_idx in range(n_chans):
#                         self.dataBuffer[samp_idx][chan_idx] -= self.mean[chan_idx]
#                         self.dataBuffer[samp_idx][chan_idx] *= self.scaling[chan_idx]
#             except (IndexError, ValueError) as e:
#                 print(f'removing trend failed. Skipping.')
#                 pass
#             except Exception as e:
#                 raise


#             # ======================================================================================================
#             # Plot
#             # ======================================================================================================
#             px_per_chunk = self.width() / self.dataTr.chunksPerScreen
#             x0 = self.chunk_idx * px_per_chunk
#             for ch_idx in range(n_chans):
#                 chan_offset = (ch_idx + 0.5) * self.channelHeight
#                 if self.lastY:
#                     if not math.isnan(self.lastY[ch_idx]) and not math.isnan(self.dataBuffer[0][ch_idx]):
#                         painter.drawLine(QPointF((x0 - self.px_per_samp),
#                                          (-self.lastY[ch_idx] + chan_offset)),
#                                         QPointF(x0,
#                                          (-self.dataBuffer[0][ch_idx] + chan_offset)))

#                 for m in range(n_samps - 1):
#                     if not math.isnan(self.dataBuffer[m][ch_idx]) and not math.isnan(self.dataBuffer[m+1][ch_idx]):
#                         painter.drawLine(QPointF((x0 + m * self.px_per_samp), (-self.dataBuffer[m][ch_idx] + chan_offset)),
#                                          QPointF((x0 + (m + 1) * self.px_per_samp),  (-self.dataBuffer[m+1][ch_idx] + chan_offset)))

#             # Reset for next iteration
#             self.chunk_idx = (self.chunk_idx + 1) % self.dataTr.chunksPerScreen  # For next iteration
#             self.lastY = self.dataBuffer[-1]
#             self.dataBuffer = None

#         if self.markerBuffer is not None:
#             painter.setPen(QPen(Qt.red))
#             for px, mrk in self.markerBuffer:
#                 painter.drawLine(px, 0, px, self.height())
#                 painter.drawText(px - 2 * self.px_per_samp, 0.95 * self.height(), mrk)
#             self.markerBuffer = None
