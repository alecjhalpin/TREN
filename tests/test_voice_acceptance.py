"""Opt-in real local model acceptance; never spends API credits."""
import base64,json,os,struct,subprocess,tempfile,unittest
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
    if os.name=='nt':
     executable=Path(bridge.proc.args[0]).resolve();private=[str(executable.parent).lower()+os.sep,str(Path(os.environ['VEYRA_TOOLS_ROOT'])/'node_modules/onnxruntime-node/bin/napi-v3/win32/x64').lower()+os.sep]
     command="(Get-Process -Id "+str(bridge.proc.pid)+").Modules | Where-Object {$_.ModuleName -in @('msvcp140.dll','msvcp140_1.dll','vcruntime140.dll','vcruntime140_1.dll')} | Select-Object -ExpandProperty FileName | ConvertTo-Json -Compress"
     module_env=dict(os.environ);module_env.pop('PSModulePath',None)
     probe=subprocess.run(['pwsh.exe','-NoProfile','-NonInteractive','-Command',command],capture_output=True,text=True,timeout=20,env=module_env)
     self.assertEqual(probe.returncode,0,probe.stderr);loaded=json.loads(probe.stdout)
     if isinstance(loaded,str):loaded=[loaded]
     self.assertTrue(loaded);self.assertTrue(all(any(name.lower().startswith(root) for root in private) for name in loaded),loaded)
     self.assertIn('msvcp140.dll',{Path(name).name.lower() for name in loaded})
     print('Verified native voice loads private Microsoft C++ runtime:',[Path(name).name for name in loaded])
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
