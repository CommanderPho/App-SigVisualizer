import logging
from PyQt5.QtCore import QThread, Qt, pyqtSignal
import pylsl
import copy

logger = logging.getLogger("phohale.sigvisualizer.DataThread")

class DataThread(QThread):
    updateStreamNames = pyqtSignal(list, int)
    sendData = pyqtSignal(list, list, list, list)
    changedStream = pyqtSignal()

    def_stream_parms = {'chunk_idx': 0, 'metadata': {}, 'srate': None, 'chunkSize': None,
                        'downSampling': None, 'downSamplingFactor': None, 'downSamplingBuffer': None,
                        'inlet': None, 'stream_idx': None, 'is_marker': False}

    def __init__(self, parent):
        super().__init__(parent)
        self.chunksPerScreen = 50  # For known sampling rate data, divide the screen into this many segments.
        self.seconds_per_screen = 2  # Number of seconds per sweep
        self.streams = []
        self.stream_params = []
        self.sig_strm_idx = -1
        logger.info(f'DataThread initialized.')

    def handle_stream_expanded(self, name):
        logger.info(f'DataThread handle_stream_expanded() started.')
        stream_names = [_['metadata']['name'] for _ in self.stream_params]
        self.sig_strm_idx = stream_names.index(name)
        self.changedStream.emit()
        logger.info(f'DataThread handle_stream_expanded() finished.')


    def update_streams(self):
        logger.info(f'DataThread update_streams() started.')
        if not self.streams:
            self.streams = pylsl.resolve_streams(wait_time=1.0)
            for k, stream in enumerate(self.streams):
                n = stream.name()
                stream_params = copy.deepcopy(self.def_stream_parms)
                stream_params['inlet'] = pylsl.StreamInlet(stream)
                # Extended meta data using info object
                info = stream_params['inlet'].info()
                channelLabels = []
                logger.info("\tGetting channel names from stream metadata...")
                ch = info.desc().child("channels").child("channel")
                for ch_ix in range(info.channel_count()):
                    #print(ch.desc())
                    print("  " + ch.child_value("label"))
                    channelLabels.append(ch.child_value("label"))
                    ch = ch.next_sibling()
                stream_params['metadata'].update({
                    "name": n,
                    "ch_count": stream.channel_count(),
                    "ch_format": stream.channel_format(),
                    "srate": stream.nominal_srate(),
                    "ch_labels": channelLabels
                })
                stream_params['is_marker'] = stream.channel_format() in ["String", pylsl.cf_string]\
                                             and stream.nominal_srate() == pylsl.IRREGULAR_RATE
                if not stream_params['is_marker']:
                    if self.sig_strm_idx < 0:
                        self.sig_strm_idx = k
                    srate = stream.nominal_srate()
                    stream_params['downSampling'] = srate > 1000
                    stream_params['chunkSize'] = round(srate / self.chunksPerScreen * self.seconds_per_screen)
                    if stream_params['downSampling']:
                        stream_params['downSamplingFactor'] = round(srate / 1000)
                        n_buff = round(stream_params['chunkSize'] / stream_params['downSamplingFactor'])
                        stream_params['downSamplingBuffer'] = [[0] * int(stream.channel_count())] * n_buff
                self.stream_params.append(stream_params)

            self.updateStreamNames.emit([_['metadata'] for _ in self.stream_params], self.sig_strm_idx)
            self.start()
        logger.info(f'DataThread update_streams() finished.')

    def run(self):
        logger.info(f'DataThread run() started.')
        if self.streams:
            logger.info(f'DataThread run() started.')
            while True:
                send_ts, send_data = [], []
                if self.sig_strm_idx >= 0:
                    params = self.stream_params[self.sig_strm_idx]
                    inlet = params['inlet']
                    pull_kwargs = {'timeout': 1}
                    if params['chunkSize']:
                        pull_kwargs['max_samples'] = params['chunkSize']
                    send_data, send_ts = inlet.pull_chunk(**pull_kwargs)
                    if send_ts and params['downSampling']:
                        for m in range(round(params['chunkSize'] / params['downSamplingFactor'])):
                            end_idx = min((m + 1) * params['downSamplingFactor'], len(send_data))
                            for ch_idx in range(int(self.streams[self.sig_strm_idx].channel_count())):
                                buf = [send_data[n][ch_idx] for n in range(m * params['downSamplingFactor'], end_idx)]
                                params['downSamplingBuffer'][m][ch_idx] = sum(buf) / len(buf)
                        send_data = params['downSamplingBuffer']
                send_mrk_ts, send_mrk_data = [], []
                is_marker = [_['is_marker'] for _ in self.stream_params]
                if any(is_marker):
                    for stream_ix, params in enumerate(self.stream_params):
                        if is_marker[stream_ix]:
                            d, ts = params['inlet'].pull_chunk()
                            send_mrk_data.extend(d)
                            send_mrk_ts.extend(ts)

                if any([send_ts, send_mrk_ts]):
                    self.sendData.emit(send_ts, send_data, send_mrk_ts, send_mrk_data)
        logger.info(f'DataThread run() finished.')

        