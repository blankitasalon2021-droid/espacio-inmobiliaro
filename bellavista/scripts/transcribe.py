import glob,json,os
from faster_whisper import WhisperModel
m=WhisperModel("medium",device="cpu",compute_type="int8")
out={}
for f in sorted(glob.glob("norm/Mi_*.mp4")):
    import subprocess,numpy as np
    a=np.frombuffer(subprocess.run(["ffmpeg","-v","error","-i",f,"-ac","1","-ar","16000","-f","s16le","-"],capture_output=True).stdout,np.int16).astype(np.float32)/32768
    segs,info=m.transcribe(a,language="es",word_timestamps=True,vad_filter=False)
    words=[];txt=[]
    for s in segs:
        txt.append(s.text)
        for w in s.words: words.append([w.word,round(w.start,2),round(w.end,2)])
    out[os.path.basename(f)]={"text":"".join(txt),"words":words}
    print(os.path.basename(f),"|","".join(txt),flush=True)
json.dump(out,open("transcripts.json","w"),ensure_ascii=False,indent=1)
