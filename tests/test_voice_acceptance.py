"""Opt-in real local model acceptance; never spends API credits."""
import base64,os,struct,tempfile,unittest
from pathlib import Path
from tool_bridge import ToolBridge

@unittest.skipUnless(os.getenv('VEYRA_MODEL_ACCEPTANCE')=='1','Real speech model acceptance is opt-in')
class VoiceAcceptance(unittest.TestCase):
 def test_generated_speech_transcribes_real_audio(self):
  with tempfile.TemporaryDirectory() as directory:
   bridge=ToolBridge(Path(directory))
   try:
    result=bridge.call('voice',{'operation':'speak','text':'Hello. Your assistant is ready. What would you like to work on?','voice':'af_heart'},timeout=600)
    self.assertTrue(list((Path(directory)/'voice_models/onnx-community/Kokoro-82M-v1.0-ONNX').rglob('*.onnx')),'Speech preview must cache under data before any transcription/setup')
    wav=base64.b64decode(result['wav']);self.assertEqual(wav[:4],b'RIFF');self.assertGreater(len(wav),10000)
    rate=struct.unpack_from('<I',wav,24)[0];samples=struct.unpack('<'+'h'*((len(wav)-44)//2),wav[44:]);audio=[]
    for i in range(int(len(samples)*16000/rate)):
     position=i*rate/16000;lower=int(position);fraction=position-lower
     audio.append((samples[lower]*(1-fraction)+samples[min(lower+1,len(samples)-1)]*fraction)/32768)
    pcm=struct.pack('<'+'f'*len(audio),*audio)
    transcript=bridge.call('voice',{'operation':'transcribe','pcm':base64.b64encode(pcm).decode(),'language':'english'},timeout=180)['text']
    ready=bridge.call('voice',{'operation':'prepare'},timeout=600);self.assertTrue(ready['ready'])
    self.assertTrue(list((Path(directory)/'voice_models/onnx-community/whisper-base').rglob('*.onnx')))
    self.assertIn('assistant',transcript.lower());self.assertIn('ready',transcript.lower());print('Verified real Whisper/Kokoro round trip:',transcript)
   finally:bridge.close()
