const { chromium } = require('playwright');
const { spawn } = require('child_process');
(async()=>{
  const out = process.argv[2], FPS=30, DUR=80, N=FPS*DUR;
  const b = await chromium.launch(); const p = await b.newPage({viewport:{width:1920,height:1080}});
  await p.goto('file://'+__dirname+'/animation.html?static');
  const ff = spawn('ffmpeg',['-y','-loglevel','error','-f','image2pipe','-framerate',String(FPS),'-c:v','mjpeg','-i','-',
    '-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',out],{stdio:['pipe','inherit','inherit']});
  for(let i=0;i<N;i++){
    await p.evaluate(t=>render(t), i/FPS);
    const buf = await p.screenshot({type:'jpeg', quality:92});
    if(!ff.stdin.write(buf)) await new Promise(r=>ff.stdin.once('drain',r));
    if(i%300==0) console.log('frame',i);
  }
  ff.stdin.end(); await new Promise(r=>ff.on('close',r)); await b.close(); console.log('done');
})();
