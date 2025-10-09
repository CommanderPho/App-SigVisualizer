import time
from random import randint, random as rand
from pylsl import StreamInfo, StreamOutlet
from pylsl.lib import string2fmt

# info = StreamInfo('BioSemi', 'EEG', 8, 100, 'float32', 'myuid34234')
# an_outlet = StreamOutlet(info)

outlet_examples_dict = {
    'ex0': StreamOutlet(StreamInfo('ex0', 'EEG', 8, 100, channel_format='float32', source_id='myuid34234')),
    'ex1': StreamOutlet(StreamInfo('ex1', 'MISC', 4, 100, channel_format='float32', source_id='myuid34234')),
    'ex2': StreamOutlet(StreamInfo('ex2', 'MISC', 5, 100, channel_format='int32', source_id='myuid34234')),
    'ex3': StreamOutlet(StreamInfo('ex3', 'Markers', 1, 0, channel_format='string', source_id='myuid34234')),
}

print("now sending data...")
while True:
    for a_stream_name, an_outlet in outlet_examples_dict.items():
        print(f"sending data to {a_stream_name}")
        a_channel_format = an_outlet.get_info().channel_format()
        print(f"\tchannel format: {a_channel_format}")
        if a_channel_format in (string2fmt['float32'], string2fmt['double64'], 0): # 'float32'
            mysample = [rand() for _ in range(an_outlet.channel_count)]
        elif a_channel_format in (string2fmt['int16'], string2fmt['int32'], 1): # 'int64'
            mysample = [randint(0, 100) for _ in range(an_outlet.channel_count)]
        elif a_channel_format in (string2fmt['string'],):
            mysample = [f"marker-{int(time.time()*1000)}"]
        else:
            raise ValueError(f'Unsupported channel format: {a_channel_format}')
        # mysample = [rand() for _ in range(an_outlet.channel_count())]
        an_outlet.push_sample(mysample)
    time.sleep(0.01)


    # mysample = [rand(), rand(), rand(), rand(), rand(), rand(), rand(), rand()]
    # outlet.push_sample(mysample)
    # time.sleep(0.01)