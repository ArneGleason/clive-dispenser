"use strict";
const byId = id => document.getElementById(id);
const root = "https://github.com/ArneGleason/clive-dispenser/";
let selected = studies.length - 1;
let slide = 0;
function draw() {
  const run = studies[selected];
  const [path, caption] = run.images[slide];
  const photo = byId("hero");
  photo.src = path;
  photo.alt = run.title + " — " + caption;
  byId("expand").href = path;
  for (const [key, value] of Object.entries({date:run.date,title:run.title,method:run.method,change:run.change,finding:run.finding,caption,counter:(slide+1)+" / "+run.images.length})) byId(key).textContent=value;
  byId("files").href=root+(run.path.endsWith(".md")?"blob/main/":"tree/main/")+run.path;
  byId("prev").disabled=slide===0;
  byId("next").disabled=slide===run.images.length-1;
  Array.from(byId("rail").children).forEach((btn,i)=>btn.setAttribute("aria-current", String(i===selected)));
}
function choose(run, imageIndex) {
  selected=run;
  slide=Math.max(0,Math.min(studies[run].images.length-1,imageIndex));
  history.replaceState(null,"","#"+studies[selected].id+"/"+(slide+1));
  draw();
}
function restore() {
  const [name, index] = location.hash.slice(1).split("/");
  const found=studies.findIndex(run=>run.id===name);
  if(found>=0){selected=found;slide=Math.max(0,Math.min(studies[found].images.length-1,(parseInt(index,10)||1)-1));}
  draw();
}
studies.forEach((run,i)=>{const btn=document.createElement("button");btn.textContent=run.title;btn.onclick=()=>choose(i,0);byId("rail").append(btn);});
byId("prev").onclick=()=>choose(selected,slide-1);
byId("next").onclick=()=>choose(selected,slide+1);
window.addEventListener("hashchange",restore);
restore();
async function loadPrompt(){
  try {
    const response=await fetch("../HANDOFF.txt",{cache:"no-cache"});
    if(!response.ok) throw Error();
    byId("prompt").textContent=(await response.text()).trim();
    byId("copy").disabled=false;
  } catch {byId("prompt").textContent="Open the prompt source below to read or copy the current handoff.";}
}
byId("copy").onclick=async()=>{
  const prompt=byId("prompt");
  try{await navigator.clipboard.writeText(prompt.textContent);byId("status").textContent="Prompt copied.";}
  catch{const range=document.createRange();range.selectNodeContents(prompt);const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);byId("status").textContent="Prompt selected. Use your browser’s Copy command.";}
};
loadPrompt();