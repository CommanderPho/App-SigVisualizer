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
        # Initialize containers before any reset
        self.stream_plots = {} ## stream name -> PlotItem
        self.stream_plot_channels = {} ## stream name -> { channel_name -> { idx, tooltip, is_enabled } }
        self.stream_graphics = {} ## stream name -> { curves: [], marker_scatter: pg.ScatterPlotItem|None, means: [], scales: [], channel_labels: [], last_x_range: tuple|None }
        self.last_x_range = None

        self.dataTr = DataThread(self)
        self.dataTr.sendData.connect(self.get_data)
        self.dataTr.changedStream.connect(self.reset)

        self.reset()
        logger.info(f'MultiStreamPlotManagingWidget initialized')


    def reset(self):
        logger.info(f'MultiStreamPlotManagingWidget reset')
        for _, plot_item in self.stream_plots.items():
            try:
                self.removeItem(plot_item)
            except Exception:
                pass
            try:
                plot_item.deleteLater()
            except Exception:
                pass
        self.stream_plots.clear()
        self.stream_plot_channels.clear()
        self.stream_graphics.clear()
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
            self.stream_plot_channels[a_stream_name] = {} ## initialize per-stream channels

            # PlotItem has no setBackground; set the ViewBox background instead
            try:
                a_plot_item.getViewBox().setBackgroundColor('w')
            except Exception:
                pass
            a_plot_item.showGrid(x=True, y=True, alpha=0.3)
            a_plot_item.hideButtons()
            # Enable built-in pyqtgraph context menu and interactions
            a_plot_item.setMenuEnabled(True)
            a_plot_item.setMouseEnabled(x=True, y=True)
            a_plot_item.setClipToView(True)
            a_plot_item.setDownsampling(mode='peak')
            a_plot_item.setAutoPan(y=False)
            # Keep y positions stationary; disable auto-visible/auto-range on Y
            a_plot_item.setAutoVisible(y=False)
            try:
                a_plot_item.getViewBox().enableAutoRange(axis=pg.ViewBox.YAxis, enable=False)
            except Exception:
                pass
            a_plot_item.setLabel('bottom', 'Time', units='s')
            a_plot_item.setLabel('left', a_stream_name)

            # Attach menu actions and y-range change tracking
            self._attach_plot_interactions(a_stream_name, a_plot_item)
            
            ## Setup channels for the plot
            ch_labels = s_meta.get("ch_labels", []) or []
            for m in range(s_meta["ch_count"]):
                channel_name: str = ch_labels[m] if m < len(ch_labels) else ""
                if not channel_name:
                    channel_name = f'Ch[{m}]'
                self.stream_plot_channels[s_meta["name"]][channel_name] = {'name': channel_name, 'idx': m, 'tooltip': f'Channel[{m+1}]', 'is_enabled': True}

            self.stream_graphics[a_stream_name] = {
                'curves': [],
                'marker_scatter': None,
                'means': [],
                'scales': [],
                'channel_labels': ch_labels,
                'last_x_range': None,
                'ts_history': [],
                'raw_history': [],
                'sample_counter': 0,
                'y_manual': False,
                'suppress_y_signal': False,
                'fit_to_band': False,
            }
        ## END for s_ix, s_meta in enumerate(metadata)...
        logger.info(f'\tMultiStreamPlotManagingWidget on_streams_updated() finished.')


            



    def get_data(self, stream_name, sig_ts, sig_buffer, marker_ts, marker_buffer):
        """Update per-stream plot for the active signal stream with a scrolling window.
        Maintains a per-stream history buffer and updates curves via setData.
        """
        logger.info(f'MultiStreamPlotManagingWidget get_data(...) started.')
        
        active_stream_name = stream_name
        if not active_stream_name or active_stream_name not in self.stream_plots:
            return

        plot_item = self.stream_plots[active_stream_name]
        state = self.stream_graphics.get(active_stream_name)
        if state is None:
            state = {
                'curves': [], 'marker_scatter': None, 'means': [], 'scales': [], 'channel_labels': [], 'last_x_range': None,
                'ts_history': [], 'raw_history': [], 'sample_counter': 0,
            }
            self.stream_graphics[active_stream_name] = state
        else:
            # Upgrade state with any missing keys for backward compatibility
            state.setdefault('curves', [])
            state.setdefault('marker_scatter', None)
            state.setdefault('means', [])
            state.setdefault('scales', [])
            state.setdefault('channel_labels', [])
            state.setdefault('last_x_range', None)
            state.setdefault('ts_history', [])
            state.setdefault('raw_history', [])
            state.setdefault('sample_counter', 0)

        # Defensive: check for valid buffer
        if not sig_buffer or not isinstance(sig_buffer, list) or not sig_buffer or not isinstance(sig_buffer[0], (list, tuple)):
            # No new data; nothing to update
            return

        n_samples = len(sig_buffer)
        n_channels_total = len(sig_buffer[0]) if n_samples > 0 else 0

        # Ensure history arrays sized to channel count
        if not state['raw_history'] or len(state['raw_history']) != n_channels_total:
            state['raw_history'] = [[] for _ in range(n_channels_total)]
            state['means'] = [0 for _ in range(n_channels_total)]
            state['scales'] = [1 for _ in range(n_channels_total)]
            state['curves'] = []
            # remove any existing curves if channel count changed
            for c in list(plot_item.listDataItems()):
                try:
                    plot_item.removeItem(c)
                except Exception:
                    pass

        # Append timestamps (or synthetic indices)
        seconds_per_screen = getattr(self.dataTr, 'seconds_per_screen', 2)
        if not sig_ts or len(sig_ts) != n_samples:
            # synthesize monotonically increasing indices as time base
            base = state['sample_counter']
            new_ts = [base + i for i in range(n_samples)]
            state['sample_counter'] = base + n_samples
            time_mode = False
        else:
            new_ts = list(sig_ts)
            time_mode = True
        state['ts_history'].extend(new_ts)

        # Append raw channel data
        for ch in range(n_channels_total):
            state['raw_history'][ch].extend([row[ch] for row in sig_buffer])

        # Trim history to time window
        if state['ts_history']:
            last_ts = state['ts_history'][-1]
            cutoff = (last_ts - seconds_per_screen) if time_mode else max(0, state['sample_counter'] - int(seconds_per_screen * 1000))
            # Find first index >= cutoff
            start_idx = 0
            for i, t in enumerate(state['ts_history']):
                if t >= cutoff:
                    start_idx = i
                    break
            if start_idx > 0:
                state['ts_history'] = state['ts_history'][start_idx:]
                for ch in range(n_channels_total):
                    state['raw_history'][ch] = state['raw_history'][ch][start_idx:]

        # Build x in window [0, seconds_per_screen]
        if state['ts_history']:
            t0 = state['ts_history'][0]
            if time_mode:
                x = [t - t0 for t in state['ts_history']]
                x_max = seconds_per_screen
            else:
                # sample index base; map to [0, len-1]
                x = [i for i in range(len(state['ts_history']))]
                x_max = len(x) if len(x) > 0 else 1
        else:
            x = []
            x_max = seconds_per_screen if time_mode else 1

        # Resolve channel labels and enabled indices for the active stream
        if not state['channel_labels']:
            try:
                ch_labels = self.dataTr.stream_params[self.dataTr.sig_strm_idx]['metadata'].get('ch_labels', [])
            except Exception:
                ch_labels = []
            state['channel_labels'] = ch_labels or []

        channel_map = self.stream_plot_channels.get(active_stream_name, {})
        enabled = [(info['idx'], name) for name, info in channel_map.items() if info.get('is_enabled', True)]
        enabled.sort(key=lambda t: t[0])
        enabled_indices = [idx for idx, _ in enabled]
        enabled_labels = [name for _, name in enabled]

        n_enabled = len(enabled_indices) if enabled_indices else n_channels_total
        spacing = CHANNEL_Y_FILL / max(n_enabled or 1, 1)
        y_offsets = [i * spacing for i in range(n_enabled or n_channels_total)]

        # Recompute robust stats over current visible window
        for ch in range(n_channels_total):
            ywin = state['raw_history'][ch]
            if ywin:
                sy = sorted(ywin)
                median = sy[len(sy)//2]
                if state.get('fit_to_band'):
                    # Fit entire visible min..max into the band's height (approx spacing)
                    yrng = max(ywin) - min(ywin)
                    iqr = yrng if yrng != 0 else 1
                else:
                    iqr = (sy[int(0.75*len(sy))] - sy[int(0.25*len(sy))]) if len(sy) > 3 else (max(ywin)-min(ywin) if max(ywin)!=min(ywin) else 1)
                state['means'][ch] = median
                state['scales'][ch] = iqr if iqr != 0 else 1

        # Ensure curves exist and setData for enabled channels
        need_rebuild = (len(state['curves']) != (len(enabled_indices) if enabled_indices else n_channels_total))
        if need_rebuild:
            for c in state['curves']:
                try:
                    plot_item.removeItem(c)
                except Exception:
                    pass
            state['curves'] = []
            if enabled_indices:
                for out_idx, ch in enumerate(enabled_indices):
                    pen = pg.mkPen(color=pg.intColor(ch, hues=max(n_channels_total, 1), values=1, maxValue=200), width=1)
                    curve = pg.PlotDataItem(pen=pen, antialias=True)
                    plot_item.addItem(curve)
                    state['curves'].append(curve)
            else:
                for ch in range(n_channels_total):
                    pen = pg.mkPen(color=pg.intColor(ch, hues=max(n_channels_total, 1), values=1, maxValue=200), width=1)
                    curve = pg.PlotDataItem(pen=pen, antialias=True)
                    plot_item.addItem(curve)
                    state['curves'].append(curve)

        # Update curve data
        if enabled_indices:
            for out_idx, ch in enumerate(enabled_indices):
                if x:
                    yraw = state['raw_history'][ch]
                    if state.get('fit_to_band'):
                        # Scale to fill band: normalize min..max to [-0.5, 0.5] of band height
                        ymin = min(yraw) if yraw else 0
                        ymax = max(yraw) if yraw else 1
                        yrng = (ymax - ymin) or 1
                        ynorm = [(((v - (ymin + yrng/2)) / yrng) + 0) / 1.0 for v in yraw]
                    else:
                        ynorm = [(((v - state['means'][ch]) / state['scales'][ch]) if state['scales'][ch] else v) for v in yraw]
                    ynorm = [v + y_offsets[out_idx] for v in ynorm]
                    state['curves'][out_idx].setData(x, ynorm)
        else:
            for ch in range(n_channels_total):
                if x:
                    yraw = state['raw_history'][ch]
                    if state.get('fit_to_band'):
                        ymin = min(yraw) if yraw else 0
                        ymax = max(yraw) if yraw else 1
                        yrng = (ymax - ymin) or 1
                        ynorm = [(((v - (ymin + yrng/2)) / yrng) + 0) / 1.0 for v in yraw]
                    else:
                        ynorm = [(((v - state['means'][ch]) / state['scales'][ch]) if state['scales'][ch] else v) for v in yraw]
                    ynorm = [v + y_offsets[ch] for v in ynorm]
                    state['curves'][ch].setData(x, ynorm)

        # Set y-axis ticks to channel labels or numbers
        if enabled_labels:
            yticks = [(y_offsets[i], enabled_labels[i]) for i in range(len(enabled_labels))]
        elif state['channel_labels'] and len(state['channel_labels']) == n_channels_total:
            yticks = [(y_offsets[i], state['channel_labels'][i]) for i in range(min(len(y_offsets), len(state['channel_labels'])))]
        else:
            yticks = [(y_offsets[i], str(i+1)) for i in range(len(y_offsets))]
        ax = plot_item.getAxis('left')
        ax.setTicks([yticks])

        # Fix Y range by default so channels remain stationary vertically,
        # but do not override if the user has manually adjusted Y.
        if y_offsets and not state.get('y_manual'):
            y_min = -spacing * 0.5
            y_max = y_offsets[-1] + spacing * 0.5
            state['suppress_y_signal'] = True
            plot_item.setYRange(y_min, y_max, padding=0.0)
            state['suppress_y_signal'] = False

        # Lock x-range to the window
        plot_item.setXRange(0, x_max, padding=0.0)
        state['last_x_range'] = (0, x_max)

        # Plot markers as scatter points at top of stack
        if marker_ts and marker_buffer and (enabled_indices or n_channels_total > 0):
            marker_x, marker_y = [], []
            top = y_offsets[-1] + spacing*0.5 if y_offsets else 0
            if time_mode and state['ts_history']:
                t0 = state['ts_history'][0]
                for ts, ms in zip(marker_ts, marker_buffer):
                    x_val = ts - t0
                    if 0 <= x_val <= x_max:
                        marker_x.append(x_val)
                        marker_y.append(top)
            # synthetic index mode: skip marker alignment unless we can map indices
            if state['marker_scatter']:
                try:
                    plot_item.removeItem(state['marker_scatter'])
                except Exception:
                    pass
                state['marker_scatter'] = None
            if marker_x:
                state['marker_scatter'] = pg.ScatterPlotItem(marker_x, marker_y, symbol='t', size=14, brush='r', pen=pg.mkPen('k', width=1))
                plot_item.addItem(state['marker_scatter'])

        logger.info(f'MultiStreamPlotManagingWidget get_data(...) finished.')

    def set_channel_enabled(self, stream_name: str, channel_name: str, enabled: bool):
        """Toggle channel visibility for a given stream."""
        if stream_name in self.stream_plot_channels and channel_name in self.stream_plot_channels[stream_name]:
            self.stream_plot_channels[stream_name][channel_name]['is_enabled'] = bool(enabled)
            # No immediate redraw; will apply on next get_data()
    
    def _attach_plot_interactions(self, stream_name: str, plot_item: pg.PlotItem) -> None:
        """Enable context menu, add Reset Y-Scale action, and watch for manual Y-range changes."""
        try:
            plot_item.setMenuEnabled(True)
            # Add custom Reset Y-Scale action into the PlotItem menu
            menu = plot_item.getMenu()
            if menu is not None:
                reset_action = menu.addAction('Reset Y-Scale')
                reset_action.triggered.connect(lambda: self.reset_y_scale(stream_name))
                # Toggle per-channel fit-to-band scaling
                def toggle_fit():
                    st = self.stream_graphics.get(stream_name)
                    if not st:
                        return
                    st['fit_to_band'] = not st.get('fit_to_band', False)
                fit_action = menu.addAction('Toggle Fit Channels to Band')
                fit_action.triggered.connect(toggle_fit)
        except Exception:
            pass

        # Track manual Y-range changes from user interactions
        try:
            vb = plot_item.getViewBox()
            # Use a closure capturing the stream name
            def on_y_changed(_vb, *args, **kwargs):
                st = self.stream_graphics.get(stream_name)
                if not st:
                    return
                if st.get('suppress_y_signal'):
                    return
                st['y_manual'] = True
            # Connect to both generic and y-specific signals for robustness
            vb.sigRangeChanged.connect(on_y_changed)
            if hasattr(vb, 'sigYRangeChanged'):
                vb.sigYRangeChanged.connect(on_y_changed)
        except Exception:
            pass

    def reset_y_scale(self, stream_name: str) -> None:
        """Restore default robust y stacking range for a specific stream and clear manual override."""
        try:
            plot_item = self.stream_plots.get(stream_name)
            state = self.stream_graphics.get(stream_name)
            if not plot_item or not state:
                return

            # Determine enabled channels for spacing
            channel_map = self.stream_plot_channels.get(stream_name, {})
            enabled = [(info['idx'], name) for name, info in channel_map.items() if info.get('is_enabled', True)]
            enabled.sort(key=lambda t: t[0])
            n_enabled = len(enabled) if enabled else (len(state.get('raw_history') or []))
            spacing = CHANNEL_Y_FILL / max(n_enabled or 1, 1)

            y_min = -spacing * 0.5
            y_max = (max(n_enabled - 1, 0) * spacing) + spacing * 0.5

            state['y_manual'] = False
            state['suppress_y_signal'] = True
            plot_item.setYRange(y_min, y_max, padding=0.0)
            state['suppress_y_signal'] = False
        except Exception:
            pass

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
