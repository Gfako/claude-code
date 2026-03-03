/*
  Page Editor Tools
  - Download: Download clean HTML with embedded images (Alt+D)
  - Save: Save current page to disk via server (Alt+S)
  - Inspect: Click any element to copy its selector (Alt+I)
  - Edit Text: Click text elements to edit inline (Alt+E)

  Usage: Add before </body>: <script src="editor.js"></script>
*/

(function() {
  var TOOL_IDS = ['cc-edit-btn','cc-inspect-btn','cc-inspect-hl','cc-inspect-tag','cc-inspect-notif','cc-save-btn','cc-save-notif','cc-dl-btn'];
  var editMode = false;
  var inspectOn = false;
  var hovered = null;
  var textTags = {H1:1,H2:1,H3:1,H4:1,H5:1,H6:1,P:1,SPAN:1,A:1,LI:1,LABEL:1,BUTTON:1,DIV:1,TD:1,TH:1,CAPTION:1,FIGCAPTION:1,BLOCKQUOTE:1,EM:1,STRONG:1,B:1,I:1,U:1,SMALL:1};
  var inlineTags = {SPAN:1,STRONG:1,EM:1,B:1,I:1,U:1,A:1,BR:1,SMALL:1,SUB:1,SUP:1,MARK:1};

  // Create elements
  var editBtn = document.createElement('div'); editBtn.id = 'cc-edit-btn'; editBtn.textContent = 'Edit Text'; document.body.appendChild(editBtn);
  var inspectBtn = document.createElement('div'); inspectBtn.id = 'cc-inspect-btn'; inspectBtn.textContent = 'Inspect'; document.body.appendChild(inspectBtn);
  var hl = document.createElement('div'); hl.id = 'cc-inspect-hl'; document.body.appendChild(hl);
  var tagEl = document.createElement('div'); tagEl.id = 'cc-inspect-tag'; document.body.appendChild(tagEl);
  var inspectNotif = document.createElement('div'); inspectNotif.id = 'cc-inspect-notif'; document.body.appendChild(inspectNotif);
  var saveBtn = document.createElement('div'); saveBtn.id = 'cc-save-btn'; saveBtn.textContent = 'Save'; document.body.appendChild(saveBtn);
  var saveNotif = document.createElement('div'); saveNotif.id = 'cc-save-notif'; document.body.appendChild(saveNotif);
  var dlBtn = document.createElement('div'); dlBtn.id = 'cc-dl-btn'; dlBtn.textContent = 'Download'; document.body.appendChild(dlBtn);

  // Styles
  var s = document.createElement('style');
  s.textContent = '#cc-edit-btn{position:fixed;bottom:24px;right:24px;z-index:999999;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;padding:12px 20px;border-radius:12px;cursor:pointer;font:600 14px/1 system-ui;box-shadow:0 4px 24px rgba(102,126,234,.4);user-select:none;transition:all .2s}#cc-edit-btn:hover{transform:translateY(-2px)}#cc-edit-btn.active{background:linear-gradient(135deg,#e94560,#c23152)}.cc-editable{cursor:text!important}.cc-editable:hover{outline:2px dashed rgba(102,126,234,.5)!important;outline-offset:2px}.cc-editable:focus{outline:2px solid #667eea!important;outline-offset:2px}#cc-inspect-btn{position:fixed;bottom:24px;right:144px;z-index:999999;background:linear-gradient(135deg,#f59e0b,#d97706);color:#fff;padding:12px 20px;border-radius:12px;cursor:pointer;font:600 14px/1 system-ui;box-shadow:0 4px 24px rgba(245,158,11,.4);user-select:none;transition:all .2s}#cc-inspect-btn:hover{transform:translateY(-2px)}#cc-inspect-btn.active{background:linear-gradient(135deg,#e94560,#c23152)}#cc-inspect-hl{position:fixed;pointer-events:none;z-index:999997;border:2px solid #f59e0b;border-radius:3px;background:rgba(245,158,11,.08);transition:all .05s ease-out;display:none}#cc-inspect-tag{position:fixed;z-index:999998;pointer-events:none;background:#1a1a2e;color:#fbbf24;padding:5px 12px;border-radius:6px;font:11px/1.4 monospace;max-width:600px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:none;box-shadow:0 4px 16px rgba(0,0,0,.4);border:1px solid rgba(245,158,11,.3)}#cc-inspect-notif,#cc-save-notif{position:fixed;top:24px;left:50%;transform:translateX(-50%);z-index:1000000;background:#1a1a2e;color:#4ade80;padding:10px 24px;border-radius:10px;font:13px/1.4 system-ui;box-shadow:0 4px 20px rgba(0,0,0,.4);border:1px solid rgba(74,222,128,.3);opacity:0;transition:opacity .25s;pointer-events:none}#cc-inspect-notif.show,#cc-save-notif.show{opacity:1}#cc-save-notif.error{color:#f87171;border-color:rgba(248,113,113,.3)}#cc-save-btn{position:fixed;bottom:24px;right:240px;z-index:999999;background:linear-gradient(135deg,#10b981,#059669);color:#fff;padding:12px 20px;border-radius:12px;cursor:pointer;font:600 14px/1 system-ui;box-shadow:0 4px 24px rgba(16,185,129,.4);user-select:none;transition:all .2s}#cc-save-btn:hover{transform:translateY(-2px)}#cc-dl-btn{position:fixed;bottom:24px;right:350px;z-index:999999;background:linear-gradient(135deg,#6366f1,#4f46e5);color:#fff;padding:12px 20px;border-radius:12px;cursor:pointer;font:600 14px/1 system-ui;box-shadow:0 4px 24px rgba(99,102,241,.4);user-select:none;transition:all .2s}#cc-dl-btn:hover{transform:translateY(-2px)}';
  document.head.appendChild(s);

  // ── EDIT TEXT ──
  function isText(el) {
    if (!textTags[el.tagName]) return false;
    if (el.id && el.id.indexOf('cc-') === 0) return false;
    if (el.closest('[id^="cc-"]')) return false;
    var hasTxt = false;
    for (var i = 0; i < el.childNodes.length; i++) { if (el.childNodes[i].nodeType === 3 && el.childNodes[i].textContent.trim()) { hasTxt = true; break; } }
    var allInline = true;
    for (var j = 0; j < el.children.length; j++) { if (!inlineTags[el.children[j].tagName]) { allInline = false; break; } }
    return hasTxt || (el.textContent.trim() && allInline && el.children.length <= 10);
  }
  function toggleEdit() {
    editMode = !editMode;
    editBtn.classList.toggle('active', editMode);
    editBtn.textContent = editMode ? 'Done Editing' : 'Edit Text';
    var els = document.querySelectorAll(editMode ? '*' : '.cc-editable');
    for (var i = 0; i < els.length; i++) {
      if (editMode && isText(els[i])) { els[i].setAttribute('contenteditable','true'); els[i].classList.add('cc-editable'); els[i].spellcheck = false; }
      else if (!editMode) { els[i].removeAttribute('contenteditable'); els[i].classList.remove('cc-editable'); }
    }
  }
  editBtn.addEventListener('click', toggleEdit);

  // ── INSPECT ──
  function getSelector(el) {
    if (el.id && el.id.indexOf('cc-') !== 0) return '#' + el.id;
    var parts = [], cur = el;
    while (cur && cur !== document.body && cur !== document.documentElement) {
      var sel = cur.tagName.toLowerCase();
      if (cur.id && cur.id.indexOf('cc-') !== 0) { parts.unshift('#' + cur.id); break; }
      if (cur.className && typeof cur.className === 'string') {
        var cls = cur.className.trim().split(/\s+/).filter(function(c){return c.indexOf('w-')!==0&&c.indexOf('cc-')!==0&&c.indexOf('w--')!==0}).slice(0,3);
        if (cls.length) sel += '.' + cls.join('.');
      }
      var p = cur.parentElement;
      if (p) { var sibs = Array.from(p.children).filter(function(c){return c.tagName===cur.tagName}); if (sibs.length>1) sel += ':nth-of-type('+(sibs.indexOf(cur)+1)+')'; }
      parts.unshift(sel); cur = p;
    }
    return parts.join(' > ');
  }
  function getInfo(el) {
    var t = el.tagName.toLowerCase(), sel = getSelector(el), txt = (el.textContent||'').trim().substring(0,80);
    var line = '<'+t+'>';
    if (el.className && typeof el.className === 'string' && el.className.trim()) line += ' class="'+el.className.trim().split(/\s+/).slice(0,4).join(' ')+'"';
    if (txt) line += ' | "'+txt+'"';
    return {display:line,selector:sel,tag:t,text:txt};
  }
  function iFlash(m){inspectNotif.textContent=m;inspectNotif.classList.add('show');setTimeout(function(){inspectNotif.classList.remove('show')},2000)}
  document.addEventListener('mousemove',function(e){
    if(!inspectOn)return;
    var el=document.elementFromPoint(e.clientX,e.clientY);
    if(!el||el.id&&el.id.indexOf('cc-')===0||el===document.body||el===document.documentElement)return;
    hovered=el;var r=el.getBoundingClientRect();
    hl.style.display='block';hl.style.left=r.left+'px';hl.style.top=r.top+'px';hl.style.width=r.width+'px';hl.style.height=r.height+'px';
    var info=getInfo(el);tagEl.style.display='block';tagEl.textContent=info.display;
    tagEl.style.left=Math.min(r.left,window.innerWidth-500)+'px';tagEl.style.top=Math.max(0,r.top-28)+'px';
  },true);
  document.addEventListener('click',function(e){
    if(!inspectOn)return;
    e.preventDefault();e.stopPropagation();e.stopImmediatePropagation();
    if(!hovered)return;
    var info=getInfo(hovered);
    var clip='Element: '+info.selector+'\nTag: <'+info.tag+'>\nText: "'+info.text+'"';
    navigator.clipboard.writeText(clip).then(function(){iFlash('Copied — paste into Claude Code')}).catch(function(){iFlash('Copy failed');console.log(clip)});
    toggleInspect();
  },true);
  function toggleInspect(){
    inspectOn=!inspectOn;inspectBtn.classList.toggle('active',inspectOn);inspectBtn.textContent=inspectOn?'Cancel':'Inspect';
    if(!inspectOn){hl.style.display='none';tagEl.style.display='none';hovered=null;document.body.style.cursor=''}
    else{document.body.style.cursor='crosshair'}
  }
  inspectBtn.addEventListener('click',toggleInspect);

  // ── SAVE TO DISK ──
  function sFlash(m,err){saveNotif.textContent=m;saveNotif.className='show'+(err?' error':'');setTimeout(function(){saveNotif.className=''},2500)}
  function saveHTML(){
    if(editMode) toggleEdit();
    var editables = document.querySelectorAll('.cc-editable');
    editables.forEach(function(el){el.removeAttribute('contenteditable');el.classList.remove('cc-editable')});
    TOOL_IDS.forEach(function(id){var el=document.getElementById(id);if(el)el.remove()});
    var html = '<!DOCTYPE html>\n' + document.documentElement.outerHTML;
    document.body.appendChild(editBtn);document.body.appendChild(inspectBtn);
    document.body.appendChild(hl);document.body.appendChild(tagEl);document.body.appendChild(inspectNotif);
    document.body.appendChild(saveBtn);document.body.appendChild(saveNotif);document.body.appendChild(dlBtn);
    fetch(window.location.origin+'/api/save',{method:'POST',body:html})
    .then(function(r){if(!r.ok)throw new Error('HTTP '+r.status);return r.text()})
    .then(function(){sFlash('Saved to disk')})
    .catch(function(err){sFlash('Save failed — use Download instead',true)});
  }
  saveBtn.addEventListener('click',saveHTML);

  // ── DOWNLOAD (shareable HTML with embedded images) ──
  function imgToBase64(img){
    return new Promise(function(resolve){
      if(!img.src||img.src.indexOf('localhost')===-1){resolve(null);return}
      var c=document.createElement('canvas');var i=new Image();i.crossOrigin='anonymous';
      i.onload=function(){c.width=i.width;c.height=i.height;c.getContext('2d').drawImage(i,0,0);resolve(c.toDataURL('image/jpeg',0.9))};
      i.onerror=function(){resolve(null)};i.src=img.src;
    });
  }
  async function downloadHTML(){
    if(editMode) toggleEdit();
    sFlash('Preparing download...');
    var clone=document.documentElement.cloneNode(true);
    clone.querySelectorAll('.cc-editable').forEach(function(el){el.removeAttribute('contenteditable');el.classList.remove('cc-editable')});
    TOOL_IDS.forEach(function(id){var el=clone.querySelector('#'+id);if(el)el.remove()});
    clone.querySelectorAll('script').forEach(function(s){if(s.src&&s.src.includes('editor.js'))s.remove()});
    clone.querySelectorAll('style').forEach(function(s){if(s.textContent.includes('cc-edit-btn')||s.textContent.includes('cc-inspect-btn')||s.textContent.includes('cc-save-btn')||s.textContent.includes('cc-dl-btn'))s.remove()});
    var imgs=document.querySelectorAll('img');var cloneImgs=clone.querySelectorAll('img');
    for(var i=0;i<imgs.length;i++){var b64=await imgToBase64(imgs[i]);if(b64&&cloneImgs[i])cloneImgs[i].src=b64}
    var html='<!DOCTYPE html>\n'+clone.outerHTML;
    var blob=new Blob([html],{type:'text/html'});var a=document.createElement('a');
    a.href=URL.createObjectURL(blob);a.download=document.title.replace(/[^a-zA-Z0-9 ]/g,'').trim().replace(/\s+/g,'-').substring(0,60)+'.html';
    a.click();URL.revokeObjectURL(a.href);sFlash('Downloaded!');
  }
  dlBtn.addEventListener('click',downloadHTML);

  // ── KEYS ──
  document.addEventListener('keydown',function(e){
    if(e.altKey&&e.key==='e'){e.preventDefault();toggleEdit()}
    if(e.altKey&&e.key==='i'){e.preventDefault();toggleInspect()}
    if(e.altKey&&e.key==='s'){e.preventDefault();saveHTML()}
    if(e.altKey&&e.key==='d'){e.preventDefault();downloadHTML()}
    if(e.key==='Escape'&&inspectOn)toggleInspect();
  });
})();
