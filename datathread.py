import logging
from PyQt5.QtCore import QThread, Qt, pyqtSignal
import pylsl
import copy

logger = logging.getLogger("phohale.sigvisualizer.DataThread")

class DataThread(QThread):
    updateStreamNames = pyqtSignal(list, int) ## emitted when the stream names are updated
    # Standardized order: (stream_name, sig_ts, sig_buffer, marker_stream_names, marker_ts, marker_buffer)
    sendData = pyqtSignal(str, list, list, list, list, list)
    # sendSingleStreamData = pyqtSignal(str, list, list) # (stream_name: str, sig_ts: NDArray, sig_buffer: NDArray)
    sendMarkerData = pyqtSignal(list, list, list) # (marker_stream_names: list, marker_ts: list, marker_buffer: list)
    
    changedStream = pyqtSignal() ## emitted when the stream selection is changed. Based off of the idea that only one stream is selected at a time.
    
    def_stream_parms = {'chunk_idx': 0, 'metadata': {}, 'srate': None, 'chunkSize': None,
                        'downSampling': None, 'downSamplingFactor': None, 'downSamplingBuffer': None,
                        'inlet': None, 'stream_idx': None, 'is_marker': False}

    def __init__(self, parent):
        super().__init__(parent)
        self.chunksPerScreen = 50  # For known sampling rate data, divide the screen into this many segments.
        self.seconds_per_screen = 2  # Number of seconds per sweep
        self.streams = []
        self.stream_params = []
        self.sig_strm_idx = -1 ## the index of the selected stream -- TODO 2025-10-09 - replace so that it works with multiple streams
        self._running = False
        logger.info(f'DataThread initialized.')

    def handle_stream_expanded(self, name):
        logger.info(f'DataThread handle_stream_expanded() started.')
        stream_names = [_['metadata']['name'] for _ in self.stream_params]
        self.sig_strm_idx = stream_names.index(name)
        self.changedStream.emit() ## emit the self.changedStream signal

        logger.info(f'DataThread handle_stream_expanded() finished.')


    def update_streams(self):
        logger.info(f'DataThread update_streams() started.')
        if not self.streams:
            self.streams = pylsl.resolve_streams(wait_time=1.0)
            for k, stream in enumerate(self.streams):
                n = stream.name()
                stream_params = copy.deepcopy(self.def_stream_parms)
                stream_params['inlet'] = pylsl.StreamInlet(stream, processing_flags=(pylsl.proc_monotonize|pylsl.proc_clocksync))
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
                stream_params['is_marker'] = (stream.channel_format() in ["String", pylsl.cf_string]) and (stream.nominal_srate() == pylsl.IRREGULAR_RATE)
                if not stream_params['is_marker']:
                    if (self.sig_strm_idx < 0):
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
            self._running = True
            self.start()
        logger.info(f'DataThread update_streams() finished.')



    def run(self):
        logger.info(f'DataThread run() started.')
        if self.streams:
            logger.info(f'DataThread run() started.')
            while self._running:
                # Aggregate markers once per loop; reuse for all numeric streams
                send_mrk_ts, send_mrk_data, send_mrk_stream_names = [], [], []
                is_marker = [_['is_marker'] for _ in self.stream_params]
                if any(is_marker):
                    for stream_ix, params in enumerate(self.stream_params):
                        if is_marker[stream_ix]:
                            d, ts = params['inlet'].pull_chunk()
                            a_stream_name: str = params['metadata'].get('name') or f'stream[{stream_ix}]'
                            ## hitting this a lot, but ts and d are always empty
                            if ts:                                
                                logger.info(f'\t marker stream [{stream_ix}] [{a_stream_name}] in .run(): {len(d)} samples, {len(ts)} timestamps.')
                                send_mrk_stream_names.extend([a_stream_name] * len(d))
                                send_mrk_data.extend(d)
                                send_mrk_ts.extend(ts)
                    ## END for stream_ix, params in enumerate(self.stream_params)...
                ## END if any(is_marker)...



                # Pull chunks for each non-marker stream and emit individually
                for stream_ix, params in enumerate(self.stream_params):
                    if params.get('is_marker'):
                        continue
                    inlet = params['inlet']
                    pull_kwargs = {'timeout': 1}
                    if params.get('chunkSize'):
                        pull_kwargs['max_samples'] = params['chunkSize']
                    sig_data, sig_ts = inlet.pull_chunk(**pull_kwargs)
                    if sig_ts and params.get('downSampling'):
                        # Downsample by simple mean over contiguous blocks
                        for m in range(round(params['chunkSize'] / params['downSamplingFactor'])):
                            end_idx = min((m + 1) * params['downSamplingFactor'], len(sig_data))
                            for ch_idx in range(int(self.streams[stream_ix].channel_count())):
                                buf = [sig_data[n][ch_idx] for n in range(m * params['downSamplingFactor'], end_idx)]
                                params['downSamplingBuffer'][m][ch_idx] = sum(buf) / len(buf)
                        sig_data = params['downSamplingBuffer']

                    if sig_ts or send_mrk_ts:
                        stream_name = params['metadata'].get('name') or f'stream_{stream_ix}'
                        # Emit in standardized order
                        # self.sendSingleStreamData.emit(stream_name, sig_ts, sig_data)
                        self.sendData.emit(stream_name, sig_ts, sig_data, send_mrk_stream_names, send_mrk_ts, send_mrk_data)
                        

                ## END for stream_ix, params in enumerate(self.stream_params):...
                ## only emit after all streams are aggregated:
                # self.sendData.emit(stream_name, sig_ts, sig_data, send_mrk_stream_names, send_mrk_ts, send_mrk_data)

                if send_mrk_ts:
                    self.sendMarkerData.emit(send_mrk_stream_names, send_mrk_ts, send_mrk_data)

            ## END while self._running:...


        logger.info(f'DataThread run() finished.')

    def stop(self):
        """Cooperatively stop the thread's loop and wait for exit."""
        try:
            self._running = False
        except Exception:
            pass
        