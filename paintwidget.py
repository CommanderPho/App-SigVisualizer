from copy import deepcopy
from datathread import DataThread
from PyQt5.QtCore import Qt, QPointF, QPoint, QLine, QLineF
from PyQt5.QtGui import QPalette, QPainter, QPen
from PyQt5.QtWidgets import QWidget
import math

CHANNEL_Y_FILL = 0.7  # How much of the per-channel vertical space is filled.  > 1 will overlap the lines.

class PaintWidget(QWidget):

    def __init__(self, widget):
        super().__init__()
        self.reset()
        pal = QPalette()
        pal.setColor(QPalette.Background, Qt.white)
        self.setAutoFillBackground(True)
        self.setPalette(pal)

        self.dataTr = DataThread(self)
        self.dataTr.sendData.connect(self.get_data)
        self.dataTr.changedStream.connect(self.reset)

    def reset(self):
        self.chunk_idx = 0
        self.channelHeight = 0
        self.px_per_samp = 0
        self.dataBuffer = None
        self.markerBuffer = None
        self.lastY = []
        self.scaling = []
        self.mean = []
        self.t0 = 0

    def get_data(self, sig_ts, sig_buffer, marker_ts, marker_buffer):
        update_x0 = float(self.width())
        update_width = 0.

        # buffer should have exactly self.dataTr.chunkSize samples or be empty
        if any(sig_ts):
            if not self.mean:
                self.mean = [0 for _ in range(len(sig_buffer[0]))]
                self.scaling = [1 for _ in range(len(sig_buffer[0]))]
            if self.chunk_idx == 0:
                self.t0 = sig_ts[0]
            self.dataBuffer = deepcopy(sig_buffer)
            px_per_chunk = self.width() / self.dataTr.chunksPerScreen
            update_x0 = self.chunk_idx * px_per_chunk
            update_width = px_per_chunk

        if any(marker_ts):
            px_out = []
            ms_out = []
            px_per_sec = self.width() / self.dataTr.seconds_per_screen
            for ts, ms in zip(marker_ts, marker_buffer):
                if any(sig_ts):  # Relative to signal timestamps
                    this_px = update_x0 + (ts - sig_ts[0]) * px_per_sec
                    if 0 <= this_px <= self.width():
                        px_out.append(this_px)
                        ms_out.append(','.join(ms))
                else:
                    # TODO: Check samples vs pixels for both data stream and marker stream.
                    # I think there is some rounding error.
                    
                    if self.t0 <= ts <= (self.t0 + self.dataTr.seconds_per_screen):
                        px_out.append((ts - self.t0) * px_per_sec)
                        ms_out.append(','.join(ms))
            if any(px_out):
                # Sometimes the marker might happen just off screen so we lose it.
                self.markerBuffer = zip(px_out, ms_out)
                update_x0 = min(update_x0, min(px_out))
                update_width = max(update_width, max([_ - update_x0 for _ in px_out]))

        if any(sig_ts) and update_x0 == sig_ts[0]:
            update_x0 -= self.px_per_samp  # Offset to connect with previous sample

        # Repaint only the region of the screen containing this data chunk.
        if update_width > 0:
            self.update(int(update_x0), 0, int(update_width + 1), self.height())

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.dataBuffer is not None:
            painter.setPen(QPen(Qt.blue))

            n_samps = len(self.dataBuffer)
            n_chans = len(self.dataBuffer[0])

            self.channelHeight = self.height() / n_chans
            self.px_per_samp = self.width() / self.dataTr.chunksPerScreen / n_samps

            # ======================================================================================================
            # Calculate Trend and Scaling
            # ======================================================================================================
            if self.chunk_idx == 0 or not self.mean:
                for chan_idx in range(n_chans):
                    samps_for_chan = [frame[chan_idx] for frame in self.dataBuffer]
                    self.mean[chan_idx] = sum(samps_for_chan) / len(samps_for_chan)

                    for m in range(len(samps_for_chan)):
                        samps_for_chan[m] -= self.mean[chan_idx]

                    data_range = (max(samps_for_chan) - min(samps_for_chan) + 0.0000000000001)
                    self.scaling[chan_idx] = self.channelHeight * CHANNEL_Y_FILL / data_range

            # ======================================================================================================
            # Trend Removal and Scaling
            # ======================================================================================================
            try:
                for samp_idx in range(n_samps):
                    for chan_idx in range(n_chans):
                        self.dataBuffer[samp_idx][chan_idx] -= self.mean[chan_idx]
                        self.dataBuffer[samp_idx][chan_idx] *= self.scaling[chan_idx]
            except (IndexError, ValueError) as e:
                print(f'removing trend failed. Skipping.')
                pass
            except Exception as e:
                raise


            # ======================================================================================================
            # Plot
            # ======================================================================================================
            px_per_chunk = self.width() / self.dataTr.chunksPerScreen
            x0 = self.chunk_idx * px_per_chunk
            for ch_idx in range(n_chans):
                chan_offset = (ch_idx + 0.5) * self.channelHeight
                if self.lastY:
                    if not math.isnan(self.lastY[ch_idx]) and not math.isnan(self.dataBuffer[0][ch_idx]):
                        painter.drawLine(QPointF((x0 - self.px_per_samp),
                                         (-self.lastY[ch_idx] + chan_offset)),
                                        QPointF(x0,
                                         (-self.dataBuffer[0][ch_idx] + chan_offset)))

                for m in range(n_samps - 1):
                    if not math.isnan(self.dataBuffer[m][ch_idx]) and not math.isnan(self.dataBuffer[m+1][ch_idx]):
                        painter.drawLine(QPointF((x0 + m * self.px_per_samp), (-self.dataBuffer[m][ch_idx] + chan_offset)),
                                         QPointF((x0 + (m + 1) * self.px_per_samp),  (-self.dataBuffer[m+1][ch_idx] + chan_offset)))

            # Reset for next iteration
            self.chunk_idx = (self.chunk_idx + 1) % self.dataTr.chunksPerScreen  # For next iteration
            self.lastY = self.dataBuffer[-1]
            self.dataBuffer = None

        if self.markerBuffer is not None:
            painter.setPen(QPen(Qt.red))
            for px, mrk in self.markerBuffer:
                painter.drawLine(px, 0, px, self.height())
                painter.drawText(px - 2 * self.px_per_samp, 0.95 * self.height(), mrk)
            self.markerBuffer = None
