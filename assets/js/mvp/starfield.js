(function(){
  var canvas = document.getElementById('starfield');
  if(!canvas) return;

  var ctx = canvas.getContext('2d');
  var section = canvas.parentElement;
  var sfWrap = document.getElementById('sf-wrap');
  var sfContent = section.querySelector('.sf-content');
  var particles = [];
  var fastPs = [];
  var staticStars = [];
  var NUM_P = 40;
  var NUM_S = 30;
  var TRAIL_LEN = 12;
  var FAST_SZ = 3.25;
  var FAST_MAX_TRAIL = 40;
  var frame = 0;
  var isImmersive = false;

  var FCOLORS = [
    { r: 26, g: 115, b: 232 },
    { r: 255, g: 193, b: 7 },
    { r: 76, g: 175, b: 80 },
    { r: 229, g: 57, b: 53 }
  ];

  var lastFastSpawn = 0;
  var nextFastDelay = 0;
  var hideEls = [
    document.querySelector('.mvp-panel'),
    document.querySelector('.topbar'),
    document.querySelector('.row-desc'),
    document.querySelector('.row-body'),
    document.querySelector('.row-sug'),
    document.querySelector('.row-roadmap'),
    document.querySelector('.row-flow'),
    document.querySelector('.footer')
  ];

  function resize(){
    if(isImmersive){
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    }else{
      canvas.width = section.offsetWidth;
      canvas.height = section.offsetHeight;
    }

    genStatic();
  }

  function genStatic(){
    staticStars = [];

    for(var i = 0; i < NUM_S; i++){
      staticStars.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        size: Math.random() * 0.8 + 0.2,
        op: Math.random() * 0.2 + 0.05,
        ph: Math.random() * Math.PI * 2,
        tw: Math.random() * 0.02 + 0.005
      });
    }
  }

  function mkP(){
    var cw = canvas.width;
    var ch = canvas.height;
    var edge = Math.floor(Math.random() * 4);
    var sx;
    var sy;

    switch(edge){
      case 0:
        sx = Math.random() * cw;
        sy = -Math.random() * 15;
        break;
      case 1:
        sx = cw + Math.random() * 15;
        sy = Math.random() * ch;
        break;
      case 2:
        sx = Math.random() * cw;
        sy = ch + Math.random() * 15;
        break;
      default:
        sx = -Math.random() * 15;
        sy = Math.random() * ch;
    }

    return {
      sx: sx,
      sy: sy,
      tx: cw / 2 + (Math.random() - 0.5) * cw * 0.2,
      ty: ch / 2 + (Math.random() - 0.5) * ch * 0.2,
      x: sx,
      y: sy,
      prog: 0,
      sz: Math.random() * 4.5 + 2,
      op: Math.random() * 0.7 + 0.5,
      spd: Math.random() * 0.004 + 0.0015,
      trail: []
    };
  }

  function mkFast(){
    var cw = canvas.width;
    var ch = canvas.height;
    var color = FCOLORS[Math.floor(Math.random() * FCOLORS.length)];

    return {
      x: Math.random() * cw,
      y: Math.random() * ch,
      angle: Math.random() * Math.PI * 2,
      speed: Math.random() * 4 + 3,
      sz: FAST_SZ,
      baseOp: Math.random() * 0.3 + 0.7,
      op: 0,
      color: color,
      trail: [],
      life: 0,
      maxLife: Math.random() * 180 + 120
    };
  }

  function toggleImmersive(){
    isImmersive = !isImmersive;

    if(isImmersive){
      hideEls.forEach(function(el){
        if(el) el.style.display = 'none';
      });
      sfContent.style.display = 'none';
      sfWrap.style.position = 'fixed';
      sfWrap.style.top = '0';
      sfWrap.style.left = '0';
      sfWrap.style.width = '100vw';
      sfWrap.style.height = '100vh';
      sfWrap.style.margin = '0';
      sfWrap.style.padding = '0';
      sfWrap.style.borderRadius = '0';
      sfWrap.style.background = '#0a0a1a';
      sfWrap.style.animation = 'none';
      sfWrap.style.zIndex = '9999';
      section.style.width = '100%';
      section.style.height = '100%';
      section.style.borderRadius = '0';
      section.style.padding = '0';
      section.style.border = 'none';
      section.style.margin = '0';
      document.body.style.background = '#0a0a1a';
      document.body.style.overflow = 'hidden';
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
      return;
    }

    hideEls.forEach(function(el){
      if(el) el.style.display = '';
    });
    sfContent.style.display = '';
    sfWrap.style.position = '';
    sfWrap.style.top = '';
    sfWrap.style.left = '';
    sfWrap.style.width = '';
    sfWrap.style.height = '';
    sfWrap.style.margin = '';
    sfWrap.style.padding = '';
    sfWrap.style.borderRadius = '';
    sfWrap.style.background = '';
    sfWrap.style.animation = '';
    sfWrap.style.zIndex = '';
    section.style.width = '';
    section.style.height = '';
    section.style.borderRadius = '';
    section.style.padding = '';
    section.style.border = '';
    section.style.margin = '';
    document.body.style.background = '';
    document.body.style.overflow = '';

    requestAnimationFrame(resize);
  }

  function init(){
    resize();
    particles = [];

    for(var i = 0; i < NUM_P; i++){
      var particle = mkP();
      particle.prog = Math.random() * 0.85;
      particle.x = particle.sx + (particle.tx - particle.sx) * particle.prog;
      particle.y = particle.sy + (particle.ty - particle.sy) * particle.prog;
      particles.push(particle);
    }

    lastFastSpawn = Date.now();
    nextFastDelay = 3000 + Math.random() * 2000;
  }

  function drawParticleTrail(trailItem, opacity, size, color){
    if(opacity <= 0.008 || size <= 0.5) return;

    var gradient = ctx.createRadialGradient(trailItem.x, trailItem.y, 0, trailItem.x, trailItem.y, size);
    gradient.addColorStop(0, 'rgba(' + color.r + ',' + color.g + ',' + color.b + ',' + opacity + ')');
    gradient.addColorStop(0.4, 'rgba(' + color.r + ',' + color.g + ',' + color.b + ',' + (opacity * 0.4) + ')');
    gradient.addColorStop(1, 'rgba(' + color.r + ',' + color.g + ',' + color.b + ',0)');
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(trailItem.x, trailItem.y, size, 0, Math.PI * 2);
    ctx.fill();
  }

  function draw(){
    frame++;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    var bg = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
    bg.addColorStop(0, '#16213e');
    bg.addColorStop(1, '#0a0a1a');
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    staticStars.forEach(function(star){
      var twinkle = Math.sin(frame * star.tw + star.ph);
      var opacity = star.op + twinkle * 0.08;
      if(opacity < 0.03) opacity = 0.03;
      ctx.beginPath();
      ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(255,255,255,' + opacity + ')';
      ctx.fill();
    });

    particles.forEach(function(particle, index){
      particle.prog += particle.spd;
      particle.x = particle.sx + (particle.tx - particle.sx) * particle.prog;
      particle.y = particle.sy + (particle.ty - particle.sy) * particle.prog;

      var currentSize = particle.sz * (1 - particle.prog * 0.85);
      var currentOpacity = particle.op * (1 - particle.prog * 0.8);

      if(currentSize > 0.3 && currentOpacity > 0.03){
        particle.trail.push({ x: particle.x, y: particle.y, sz: currentSize, op: currentOpacity });
        if(particle.trail.length > TRAIL_LEN) particle.trail.shift();
      }

      if(particle.prog >= 1 || currentSize < 0.2 || currentOpacity < 0.02){
        particles[index] = mkP();
        return;
      }

      particle.trail.forEach(function(trailItem, trailIndex){
        var age = (trailIndex + 1) / particle.trail.length;
        drawParticleTrail(trailItem, trailItem.op * age * 0.28, trailItem.sz * 2.5, { r: 255, g: 255, b: 255 });
      });

      if(currentSize > 0.3 && currentOpacity > 0.03){
        var glow = ctx.createRadialGradient(particle.x, particle.y, 0, particle.x, particle.y, currentSize * 3);
        glow.addColorStop(0, 'rgba(255,255,255,' + (currentOpacity * 0.18) + ')');
        glow.addColorStop(1, 'rgba(255,255,255,0)');
        ctx.fillStyle = glow;
        ctx.beginPath();
        ctx.arc(particle.x, particle.y, currentSize * 3, 0, Math.PI * 2);
        ctx.fill();

        ctx.beginPath();
        ctx.arc(particle.x, particle.y, currentSize, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(255,255,255,' + currentOpacity + ')';
        ctx.fill();
      }
    });

    var now = Date.now();
    if(now - lastFastSpawn >= nextFastDelay){
      var fastParticle = mkFast();
      fastParticle.op = fastParticle.baseOp;
      fastPs.push(fastParticle);
      lastFastSpawn = now;
      nextFastDelay = 3000 + Math.random() * 2000;
    }

    for(var i = fastPs.length - 1; i >= 0; i--){
      var fp = fastPs[i];
      fp.life++;
      fp.op = fp.baseOp * (1 - fp.life / fp.maxLife);
      fp.x += Math.cos(fp.angle) * fp.speed;
      fp.y += Math.sin(fp.angle) * fp.speed;

      if(fp.op > 0.02){
        fp.trail.push({ x: fp.x, y: fp.y, sz: fp.sz, op: fp.op });
        if(fp.trail.length > FAST_MAX_TRAIL) fp.trail.shift();
      }

      if(fp.op < 0.02 || fp.x < -60 || fp.x > canvas.width + 60 || fp.y < -60 || fp.y > canvas.height + 60){
        fastPs.splice(i, 1);
        continue;
      }

      fp.trail.forEach(function(trailItem, trailIndex){
        var age = (trailIndex + 1) / fp.trail.length;
        drawParticleTrail(trailItem, trailItem.op * age * 0.32, trailItem.sz * 2.2, fp.color);
      });

      if(fp.op > 0.03){
        var fastGlow = ctx.createRadialGradient(fp.x, fp.y, 0, fp.x, fp.y, fp.sz * 3);
        fastGlow.addColorStop(0, 'rgba(' + fp.color.r + ',' + fp.color.g + ',' + fp.color.b + ',' + (fp.op * 0.25) + ')');
        fastGlow.addColorStop(1, 'rgba(' + fp.color.r + ',' + fp.color.g + ',' + fp.color.b + ',0)');
        ctx.fillStyle = fastGlow;
        ctx.beginPath();
        ctx.arc(fp.x, fp.y, fp.sz * 3, 0, Math.PI * 2);
        ctx.fill();

        ctx.beginPath();
        ctx.arc(fp.x, fp.y, fp.sz, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(' + fp.color.r + ',' + fp.color.g + ',' + fp.color.b + ',' + fp.op + ')';
        ctx.fill();
      }
    }

    requestAnimationFrame(draw);
  }

  sfWrap.addEventListener('dblclick', function(event){
    if(isImmersive){
      toggleImmersive();
      return;
    }

    var clarifyBox = section.querySelector('.clarify-box');
    var secHdEl = section.querySelector('.sec-hd');
    if(clarifyBox && clarifyBox.contains(event.target)) return;
    if(secHdEl && secHdEl.contains(event.target)) return;
    toggleImmersive();
  });

  init();
  draw();
  window.addEventListener('resize', resize);
})();
