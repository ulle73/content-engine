/* The browser presents plans. Only explicit action buttons can approve a job. */
const app = document.getElementById('assistant-app');
if (app) {
  const {motionStudio}=await import(app.dataset.motionModule);
  const byId = id => document.getElementById(id);
  const catalog = JSON.parse(byId('assistant-catalog').textContent);
  let state = JSON.parse(byId('assistant-state').textContent);
  let motionSourceRender=null;
  let conversation = app.dataset.conversation, attachments = [], sending = false, uploadBusy = false, actionBusy = false;
  let draftKey = crypto.randomUUID(), pendingPayload = null, searchTimer, pollTimer, nextPage = null, libraryRequest = 0, modelSearch = '';
  const base = app.dataset.baseUrl;
  const storageKey = () => 'content-engine-studio:'+app.dataset.user+':'+base+':'+(conversation||'new');
  function saveDraft() {
    try { sessionStorage.setItem(storageKey(),JSON.stringify({message:byId('assistant-message').value, attachments,motionSourceRender,
      choices:Object.fromEntries(['workflow','model','shape','priority','template','image-policy','max-cost'].map(name=>[name,byId('assistant-'+name).value]))})); } catch { /* Privacy mode or quota: server-saved turns remain available. */ }
  }
  const csrf = byId('assistant-composer').querySelector('[name=csrfmiddlewaretoken]').value;
  const roles = [['reference', 'Referens / material'], ['start', 'Startbild'], ['end', 'Slutbild'], ['logo', 'Logga'], ['audio', 'Ljud']];
  const statusLabels = {queued:'Förberett · väntar på godkännande', starting:'Startar', running:'Arbetar', saving:'Sparar resultat', completed:'Klart', failed:'Misslyckades', canceled:'Avbrutet', unknown:'Leverantörens status behöver kontrolleras', saved:'Projektet är sparat'};
  const feedback = (text, error=false) => { byId('assistant-feedback').textContent=text; byId('assistant-feedback').classList.toggle('error',error); };
  function node(tag, text='', className='') { const el=document.createElement(tag); el.textContent=text; if(className) el.className=className; return el; }
  function button(text, callback, className='assistant-secondary') { const el=node('button',text,className); el.type='button'; el.addEventListener('click',callback); return el; }
  function media(asset) { const el=document.createElement(asset.kind==='image'?'img':asset.kind==='audio'?'audio':'video'); el.src=asset.url; el.className='assistant-result-media'; if(asset.kind==='image') { el.alt=asset.label; el.loading='lazy'; } else { el.controls=true; el.preload='metadata'; } return el; }
  function link(text, url) { const el=node('a',text,'assistant-subtle'); el.href=url; return el; }
  async function api(path, body=null) {
    const response=await fetch(base+path,{method:body===null?'GET':'POST',credentials:'same-origin',headers:body===null?{'Accept':'application/json'}:{'Content-Type':'application/json','X-CSRFToken':csrf,'Accept':'application/json'},...(body===null?{}:{body:JSON.stringify(body)})});
    const type=response.headers.get('content-type')||'';
    if(!type.includes('application/json')) throw Error('Sessionen kan ha gått ut. Ladda om sidan; dina sparade samtal finns kvar.');
    const data=await response.json(); if(!response.ok) throw Error(data.error||'Åtgärden kunde inte slutföras.'); return data;
  }
  function updateModels() {
    const selected=byId('assistant-model').value, chosen=byId('assistant-workflow').value, workflow=chosen==='auto'?(catalog.templates.find(item=>item.id===byId('assistant-template').value)?.kind||chosen):chosen;
    const models=workflow==='image'?catalog.models.image:['video','sequence'].includes(workflow)?catalog.models.video:['auto','motion'].includes(workflow)?[...catalog.models.image,...catalog.models.video]:[];
    const unique=new Map(models.map(item=>[item.id,item]));
    const select=byId('assistant-model'); select.replaceChildren(node('option','Auto · rekommenderad')); select.options[0].value='';
    for(const item of unique.values()) { const opt=node('option',item.label); opt.value=item.id; select.append(opt); }
    const remotion=node('option','Remotion');remotion.value='remotion';select.append(remotion);
    if(selected&&selected!=='remotion'&&!unique.has(selected)) { const opt=node('option',selected+' · kontrollera stöd'); opt.value=selected; select.append(opt); }
    select.value=workflow==='motion'?'remotion':selected; select.disabled=sending||uploadBusy;
    pickerMenus();
  }
  function updateTemplates() {
    const select=byId('assistant-template'), selected=select.value;
    select.replaceChildren(node('option','Egen idé')); select.options[0].value='';
    byId('template-existing').replaceChildren(node('option','Ny mall')); byId('template-existing').options[0].value='';
    for(const item of catalog.templates) { for(const target of [select,byId('template-existing')]) { const opt=node('option',item.title+' · v'+item.version); opt.value=item.id; target.append(opt); } }
    if(catalog.templates.some(item=>item.id===selected)) select.value=selected;
    templateDescription();
  }
  function pickerMenus() {
    const model=byId('assistant-model'),template=byId('assistant-template');
    byId('assistant-model-label').textContent=model.selectedOptions[0]?.textContent?.replace(' · rekommenderad','')||'Auto';
    byId('assistant-template-label').textContent=catalog.templates.find(item=>item.id===template.value)?.title||'Mall';
    for(const [name,select] of [['model',model],['template',template]]) {
      const menu=byId('assistant-'+name+'-menu');menu.replaceChildren();
      let lastGroup='';
      if(name==='model') {
        const search=node('input');search.type='search';search.placeholder='Sök modell…';search.setAttribute('aria-label','Sök bild- eller videomodell');search.value=modelSearch;search.className='assistant-model-search';
        search.addEventListener('input',()=>{modelSearch=search.value;filterModels(menu);});menu.append(search);
        menu.append(node('p','Prisindikationer gäller 10 s, före rabatter. Exakt pris och kompatibilitet kontrolleras med din plan.','assistant-model-note'));
      }
      for(const option of select.options) {
        const item=catalog.templates.find(item=>item.id===option.value);
        const profiles=[...catalog.models.image,...catalog.models.video].filter(item=>item.id===option.value);
        const group=option.value&&name==='model'?(option.value==='remotion'?'Motion':catalog.models.image.some(item=>item.id===option.value)?'Bild':'Video'):'';
        if(group&&group!==lastGroup){menu.append(node('p',group,'assistant-menu-group'));lastGroup=group;}
        const choice=button('',()=>{select.value=option.value;select.dispatchEvent(new Event('change',{bubbles:true}));select.dispatchEvent(new Event('input',{bubbles:true}));byId('assistant-'+name+'-picker').open=false;pickerMenus();},'');
        choice.append(node('span',option.value?option.textContent: name==='model'?'Auto · föreslå bästa modell':'Egen idé'));
        const supportsEnd=profiles.some(item=>item.roles.includes('END_IMAGE'));
        const chosen=byId('assistant-workflow').value, workflow=chosen==='auto'?(catalog.templates.find(item=>item.id===template.value)?.kind||chosen):chosen;
        const needsEnd=workflow==='sequence'||attachments.some(asset=>asset.role==='end');
        const mode=attachments.some(asset=>asset.role==='start')||needsEnd?'image-to-video':'text-to-video';
        const profile=profiles.find(item=>item.mode===mode)||profiles[0];
        let reason='';
        if(name==='model'&&option.value) {
          if(group==='Bild'&&(['video','sequence'].includes(workflow)||needsEnd))reason='Passar inte: bildmodellen kan inte skapa video.';
          else if(group==='Video'&&needsEnd&&!supportsEnd)reason='Passar inte: saknar stöd för slutbild.';
          else if(group==='Video'&&profile?.aspect_behavior==='explicit'&&!profile.ratios.includes({portrait:'9:16',square:'1:1',landscape:'16:9'}[byId('assistant-shape').value]))reason='Passar inte i valt bildformat.';
        }
        const description=name==='template'?(item?.instructions.replace(/\{\{[^}]+\}\}/g,'din idé').slice(0,160)||'Beskriv fritt vad du vill skapa.'):(option.value==='remotion'?'Animera text, logga och ditt material. Förhandsvisa och redigera till höger. Renderas på din anslutna dator.':option.value?(reason||profile?.summary||(group==='Bild'?'Skapa en bild eller bearbeta en referensbild.':supportsEnd?'Start- och slutbild · sammanhängande övergångar.':'Text eller startbild · saknar stöd för slutbild.')):'Vi rekommenderar en kompatibel modell inom din budget och visar varför.');
        choice.append(node('small',description));
        if(name==='model'&&option.value&&group==='Video') {
          const rates=profile?.rates||{},resolution=profile?.resolutions.includes('720p')?'720p':profile?.resolutions[0]||'',rate=Number(rates[resolution]);
          const hint=Number.isFinite(rate)?'10 s'+(resolution?' · '+resolution:'')+' ≈ $'+(10*rate).toFixed(2):'Pris kontrolleras före start';
          const cost=node('small',hint+(Number.isFinite(rate)&&10*rate>Number(byId('assistant-max-cost').value)?' · över din budget för 10 s':''),'assistant-model-cost');choice.append(cost);
        }
        choice.dataset.modelSearch=(option.textContent+' '+description).toLocaleLowerCase('sv');
        choice.setAttribute('aria-pressed',String(select.value===option.value));choice.disabled=sending||uploadBusy||Boolean(reason);menu.append(choice);
      }
      if(name==='model'){menu.append(node('p','API-utbudet skiljer sig från Higgsfield-appen. Preview-modeller väljs aldrig automatiskt.','assistant-model-note'));const empty=node('p','Ingen modell matchar sökningen.','assistant-model-empty');empty.setAttribute('role','status');menu.append(empty);filterModels(menu);}
      if(name==='template')menu.append(button('＋ Skapa eller ändra mall',()=>{byId('assistant-template-picker').open=false;updateTemplates();byId('assistant-template-dialog').showModal();},'assistant-subtle'));
    }
  }
  function filterModels(menu) {
    const query=modelSearch.trim().toLocaleLowerCase('sv');
    for(const choice of menu.querySelectorAll('button'))choice.hidden=Boolean(query&&!choice.dataset.modelSearch.includes(query));
    const empty=menu.querySelector('.assistant-model-empty');if(empty)empty.hidden=Array.from(menu.querySelectorAll('button')).some(choice=>!choice.hidden);
    for(const heading of menu.querySelectorAll('.assistant-menu-group')) {
      let next=heading.nextElementSibling,visible=false;
      while(next&&!next.classList.contains('assistant-menu-group')){if(next.tagName==='BUTTON'&&!next.hidden)visible=true;next=next.nextElementSibling;}heading.hidden=!visible;
    }
  }
  function templateDescription() { const item=catalog.templates.find(item=>item.id===byId('assistant-template').value); byId('assistant-template-description').textContent=item?item.instructions:''; pickerMenus(); }
  function restoreChoices(turn) {
    if(!turn) return;
    motionSourceRender=turn.request.motion_source_render||null;
    for(const name of ['workflow','shape','priority','template']) byId('assistant-'+name).value=turn.request[name]||({workflow:'auto',shape:'portrait',priority:'balanced'}[name]||'');
    updateModels(); const model=turn.request.model||''; if(model&&!Array.from(byId('assistant-model').options).some(opt=>opt.value===model)) { const opt=node('option',model); opt.value=model; byId('assistant-model').append(opt); } byId('assistant-model').value=model;
    attachments=turn.attachments.filter(item=>item.url); renderAttachments(); templateDescription();
    byId('assistant-image-policy').value=turn.request.image_policy||'contain';byId('assistant-max-cost').value=turn.request.max_cost_usd||'5.00';
  }
  function renderAttachments() {
    pickerMenus();
    const target=byId('assistant-attachments'); target.replaceChildren();
    for(const [index,asset] of attachments.entries()) {
      const row=node('div','','assistant-attachment');
      if(asset.kind==='image') { const img=node('img'); img.src=asset.url; img.alt=asset.label; row.append(img); } else row.append(node('span',asset.kind==='audio'?'Ljud':'Video','file-name'));
      const info=node('div'); info.append(node('span',asset.label,'file-name'));
      const select=node('select'); select.setAttribute('aria-label','Roll för '+asset.label);
      for(const [value,label] of roles) { const opt=node('option',label); opt.value=value; opt.disabled=['start','end','logo'].includes(value)&&asset.kind!=='image'||value==='audio'&&!['audio','video'].includes(asset.kind); select.append(opt); }
      select.value=asset.role; select.disabled=sending; select.addEventListener('change',()=>{asset.role=select.value;pickerMenus(); pendingPayload=null; draftKey=crypto.randomUUID();saveDraft();}); info.append(select); row.append(info);
      const remove=button('×',()=>{attachments.splice(index,1); pendingPayload=null; draftKey=crypto.randomUUID(); renderAttachments();saveDraft();}); remove.setAttribute('aria-label','Ta bort '+asset.label); remove.disabled=sending; row.append(remove); target.append(row);
      if(asset.width)info.append(node('small',asset.width+' × '+asset.height));
      const order=node('div','','assistant-order');order.append(node('small','Bild '+(index+1)));
      for(const [delta,label] of [[-1,'← Flytta'],[1,'Flytta →']]){const move=button(label,()=>{const other=index+delta;[attachments[index],attachments[other]]=[attachments[other],attachments[index]];pendingPayload=null;draftKey=crypto.randomUUID();renderAttachments();saveDraft();});move.disabled=sending||index+delta<0||index+delta>=attachments.length;move.setAttribute('aria-label','Flytta '+asset.label+(delta<0?' tidigare':' senare'));order.append(move);}row.append(order);
    }
  }
  function addAsset(asset, role=byId('assistant-file-role').value) {
    if(attachments.some(item=>item.asset_id===asset.asset_id&&item.role===role))throw Error('Filen är redan tillagd i denna roll.');
    if(attachments.length>=8) throw Error('Du kan bifoga högst åtta filer.');
    if(['start','end','logo'].includes(role)&&asset.kind!=='image') throw Error('Välj en bild för denna roll.');
    if(role==='audio'&&!['audio','video'].includes(asset.kind)) throw Error('Välj en ljudfil eller video för ljudrollen.');
    const existing=attachments.findIndex(item=>item.role===role);
    if(existing>=0&&role!=='reference') attachments.splice(existing,1);
    attachments.push({...asset,role}); pendingPayload=null; draftKey=crypto.randomUUID(); renderAttachments();saveDraft();
    if(role!=='reference')byId('assistant-library').close();byId('assistant-library-status').textContent=attachments.length+' filer valda. Lägg till fler eller stäng biblioteket.'; feedback(asset.label+' är tillagd som '+roles.find(item=>item[0]===role)[1].toLowerCase()+'.');
  }
  function renderMessages() {
    app.dataset.empty=String(state.turns.length===0);
    const root=byId('assistant-messages'); root.replaceChildren(); byId('assistant-empty').hidden=state.turns.length>0;
    for(const turn of state.turns) {
      const user=node('article','','assistant-message user'); user.append(node('strong','Du','assistant-message-label'),node('p',turn.request.message));
      const files=node('div','','assistant-message-attachments'); for(const asset of turn.attachments||[]) { if(asset.kind==='image'&&asset.url) { const img=node('img'); img.src=asset.url; img.alt=asset.label+' · '+asset.role; img.loading='lazy'; files.append(img); } else files.append(node('span',asset.label+' · '+asset.role)); } user.append(files); root.append(user);
      const answer=node('article','','assistant-message'); answer.append(node('strong','Content Engine','assistant-message-label'));
      answer.append(node('p',turn.status==='planning'?'Förbereder svar…':turn.status==='failed'?turn.error:turn.response.answer));
      if(turn.status==='failed') answer.append(button('Försök igen',()=>{byId('assistant-message').value=turn.request.message; restoreChoices(turn); pendingPayload=null; draftKey=crypto.randomUUID(); byId('assistant-message').focus();}));
      if(turn.plan?.current) for(const question of turn.response.questions||[]) { const block=node('div','','assistant-questions'); block.append(node('p',question.text)); const choices=node('div','','assistant-question-options'); for(const option of question.options) choices.append(button(option,()=>{const text=byId('assistant-message'); text.value+=(text.value?'\n':'')+question.text+' '+option; text.focus();})); block.append(choices); answer.append(block); }
      root.append(answer);
    }
    byId('assistant-title').textContent=state.title||'Vad vill du skapa?';
    if(conversation) {const nav=document.querySelector('.assistant-projects nav');const url=base+conversation+'/';let current=Array.from(nav.querySelectorAll('a')).find(item=>item.getAttribute('href')===url);if(!current){nav.querySelector('p')?.remove();current=link(state.title,url);nav.prepend(current);}current.textContent=state.title;current.setAttribute('aria-current','page');}
  }
  function renderPlan() {
    const target=byId('assistant-plan'), turn=[...state.turns].reverse().find(item=>item.plan);
    target.replaceChildren();
    if(!turn) return;
    const plan=turn.plan, spec=plan.spec, review=spec.review||{}, compiled=spec.compiled||{}, prepared=plan.prepared||{}, block=node('div','','assistant-plan-block');
    block.append(node('p','Version '+turn.revision+(plan.current?' · aktuell':' · tidigare plan'),'assistant-version'),node('h3',spec.proposal.title));
    block.append(node('strong',prepared.kind?'2 · Optimerat och förberett':'1 · Bekräfta att vi förstått dig rätt'));
    const meta=node('div','','assistant-plan-meta'); meta.append(node('strong',compiled.model_label||review.model_label||catalog.workflows.find(item=>item.id===spec.workflow)?.label||spec.workflow),node('span',({'portrait':'9:16','square':'1:1','landscape':'16:9'})[spec.options.shape])); block.append(meta);
    const params=compiled.parameters||{};if(params.duration)meta.append(node('span',params.duration+' sekunder'));if(params.resolution)meta.append(node('span',params.resolution));if(params.generate_audio!==undefined)meta.append(node('span',params.generate_audio?'Med genererat ljud':'Utan genererat ljud'));
    block.append(node('p',spec.brief,'assistant-plan-brief'));
    if(review.scene_changes?.length){const changes=node('div','','assistant-review-assets');changes.append(node('strong','Föreslagna scenändringar'));for(const change of review.scene_changes)changes.append(node('p',`Scen ${change.scene} · ${change.field}: ${change.before||'(tomt)'} → ${change.after||'(tomt)'}`));block.append(changes);}
    if(review.recommendation){const recommended=node('div','','assistant-review-cost');recommended.append(node('strong','Rekommenderad: '+review.recommendation.model_label),node('p',review.recommendation.reason));block.append(recommended);if(plan.current&&!prepared.kind&&review.recommendation.model_id&&review.recommendation.model_id!==spec.options.model)recommended.append(button('Använd rekommenderad modell',()=>{byId('assistant-model').value=review.recommendation.model_id;pickerMenus();byId('assistant-message').value='Använd den rekommenderade modellen. Behåll övriga instruktioner och material.';saveDraft();byId('assistant-message').focus();}));}
    if(review.assets?.length){const checks=node('div','','assistant-review-assets');checks.append(node('strong','Ditt material · i denna ordning'));for(const asset of review.assets){const check=node('div','','assistant-review-asset');check.append(node('strong',asset.position+'. '+asset.label),node('div',(roles.find(item=>item[0]===asset.role)?.[1]||asset.role)+(asset.width?' · '+asset.width+' × '+asset.height:'')));for(const warning of asset.warnings)check.append(node('p','⚠ '+warning));checks.append(check);}block.append(checks);}
    if(review.price_note){const costBlock=node('div','','assistant-review-cost');costBlock.append(node('strong',review.total_usd===null?'Priset behöver kontrolleras':'Kostnadsförslag: $'+Number(review.total_usd).toFixed(4)),node('p','Din maxkostnad: $'+Number(review.max_cost_usd).toFixed(2)+' · '+review.count+(spec.workflow==='sequence'?' övergångar':' generation(er)')));if(spec.workflow==='sequence')for(const [index,clip]of review.clips.entries())costBlock.append(node('p','Klipp '+(index+1)+' · '+(clip.duration||'?')+' sek · '+(clip.resolution||'')+' · '+(clip.usd===null?'pris saknas':'$'+Number(clip.usd).toFixed(4))));costBlock.append(node('small',review.price_note));if(review.over_budget)costBlock.append(node('p','Över din maxkostnad. Ändra budgeten eller upplägget och skicka igen.'));block.append(costBlock);}
    if(spec.workflow==='text') block.append(node('p',compiled.prompt||spec.proposal.caption,'assistant-plan-brief'));
    if(compiled.prompt&&spec.workflow!=='text') { const detail=node('details'); detail.append(node('summary','Visa modellens prompt'),node('pre',compiled.prompt)); block.append(detail); }
    for(const warning of review.warnings||compiled.warnings||[]) block.append(node('p',warning,'assistant-plan-notice'));
    if(compiled.finish_note)block.append(node('p',compiled.finish_note,'assistant-plan-notice'));
    const imageChecks=block.querySelector('.assistant-review-assets'),costCards=block.querySelectorAll('.assistant-review-cost');if(imageChecks&&costCards.length>1)block.insertBefore(costCards[costCards.length-1],imageChecks);
    if(spec.blocked) block.append(node('p',spec.blocked,'assistant-plan-notice'));
    const cost=turn.usage?.cost_usd; if(cost!==null&&cost!==undefined) block.append(node('p','AI-samtal för detta svar: $'+Number(cost).toFixed(4),'assistant-cost-note'));
    if(!plan.current) block.append(node('p','Ett nyare meddelande finns. Vänta på den nya planen eller försök igen innan du kör.','assistant-plan-notice'));
    else if(spec.proposal.questions?.length) block.append(node('p','Besvara frågorna i samtalet för att färdigställa planen.','assistant-plan-notice'));
    else if(!spec.blocked&&!review.over_budget&&!prepared.kind) block.append(button('Bekräfta upplägget och optimera',()=>runAction(plan,'prepare'),''));
    if(prepared.url) block.append(link('Öppna hela projektet →',prepared.url));
    if(plan.budget){const budget=plan.budget;block.append(node('p',budget.verified?'Aktuellt kontrollerat totalpris: $'+Number(budget.total_usd).toFixed(4)+' · Max $'+Number(budget.max_cost_usd).toFixed(2):'Ett verifierat pris saknas. Betald start är spärrad av din maxkostnad.','assistant-plan-notice'));if(budget.over_budget)block.append(node('p','Aktuellt pris överstiger din budget. Ingen generation kan startas. Ändra budget eller upplägg i rutan och skicka igen.','assistant-plan-notice'));}
    if(plan.clips){for(const [index,clip] of plan.clips.entries()){const card=node('div','','assistant-review-asset');card.append(node('strong','Klipp '+(index+1)+' · Bild '+(index+1)+' → '+(index+2)),node('p',statusLabels[clip.status]||clip.status));const optimized=compiled.clips?.[index];if(optimized){const details=node('details');details.append(node('summary','Optimerad prompt för '+optimized.model_label),node('pre',optimized.prompt));card.append(details);}if(clip.usage?.estimate?.usd!==undefined)card.append(node('p','Kontrollerat pris: $'+Number(clip.usage.estimate.usd).toFixed(4)));if(clip.error)card.append(node('p',clip.error,'assistant-plan-notice'));if(plan.current&&clip.can_start)card.append(button('Godkänn och starta klipp '+(index+1),()=>runAction(plan,'start',clip.id),''));if(plan.current&&['queued','starting','running','saving'].includes(clip.status))card.append(button('Avbryt klipp '+(index+1),()=>runAction(plan,'cancel',clip.id)));for(const asset of clip.assets)card.append(media(asset));block.append(card);}if(plan.current)block.append(button('Uppdatera priskontrollen för alla klipp',()=>runAction(plan,'prepare')));if(plan.current&&plan.clips.length&&plan.clips.every(clip=>clip.status==='completed')&&!prepared.finish_project_id)block.append(button('Godkänn klippen och förbered slutfilm',()=>runAction(plan,'compose'),''));}
    if(plan.job) {
      const job=plan.job; block.append(node('strong',statusLabels[job.status]||job.status));
      const estimate=job.usage?.estimate;
      if(estimate?.usd!==undefined) block.append(node('p','Uppskattad generation: $'+Number(estimate.usd).toFixed(4),'assistant-plan-notice'));
      if(job.usage?.price_note) block.append(node('p',job.usage.price_note,'assistant-plan-notice'));
      if(job.error) block.append(node('p',job.error,'assistant-plan-notice'));
      if(plan.current&&job.can_start) block.append(button('Godkänn och starta betald generation',()=>runAction(plan,'start'),''));
      if(plan.current&&['queued','starting','running','saving'].includes(job.status)) block.append(button('Avbryt jobbet',()=>runAction(plan,'cancel')));
      if(plan.current&&job.status==='queued'&&!job.can_start) block.append(button('Uppdatera priskontrollen',()=>runAction(plan,'prepare')));
      for(const asset of job.assets||[]) block.append(media(asset),link('Öppna fil',asset.url));
      if(plan.current&&job.status==='completed'&&compiled.finishing&&!prepared.finish_project_id)block.append(button('Lägg på logga och avslut med Motion',()=>runAction(plan,'compose'),''));
      if(plan.current&&job.status==='completed')for(const asset of job.assets||[])block.append(button('Använd resultatet som material',()=>{attachments=attachments.filter(item=>!['start','end','reference'].includes(item.role));attachments.push({...asset,role:'reference'});byId('assistant-workflow').value=asset.kind==='video'?'motion':'auto';byId('assistant-model').value='';updateModels();renderAttachments();byId('assistant-message').value='Återanvänd det färdiga materialet och ändra bara avslutet.';saveDraft();byId('assistant-message').focus();}));
    }
    if(plan.motion) {
      if(prepared.finish_url)block.append(link('Öppna filmsteget →',prepared.finish_url));
      const motion=plan.motion; block.append(node('strong',motion.status==='queued'?'Väntar på renderaren':statusLabels[motion.status]||motion.status));
      if(!motion.available) block.append(node('p','Starta Motion-renderaren på din dator för att rendera. Projektet är sparat.','assistant-plan-notice'));
      if(motion.error) block.append(node('p',motion.error,'assistant-plan-notice'));
    }
    for(const el of block.querySelectorAll('button')) el.disabled=actionBusy||sending;
    if(plan.current&&Number(byId('assistant-max-cost').value)!==Number(spec.options.max_cost_usd??5)){block.append(node('p','Din budget har ändrats. Skicka ett nytt meddelande för att granska planen med den nya maxkostnaden.','assistant-plan-notice'));for(const el of block.querySelectorAll('button'))if(!el.textContent.startsWith('Avbryt'))el.disabled=true;}
    if(plan.budget&&(!plan.budget.verified||plan.budget.over_budget))for(const el of block.querySelectorAll('button'))if(el.textContent.startsWith('Godkänn och starta'))el.disabled=true;
    target.append(block);
  }
  const workbench=motionStudio({app,node,button,media,link,onAction:(plan,action,extra={})=>runAction(plan,action,null,extra),onComment:(turn,text,renderId)=>{
    restoreChoices(turn);byId('assistant-workflow').value='motion';byId('assistant-model').value='remotion';updateModels();
    motionSourceRender=renderId;
    byId('assistant-message').value=text;pendingPayload=null;draftKey=crypto.randomUUID();saveDraft();byId('assistant-composer').requestSubmit();
  }});
  function render() { renderMessages(); renderPlan(); workbench.render(state); schedulePoll(); }
  function schedulePoll() {
    clearTimeout(pollTimer);
    const active=state.turns.some(turn=>turn.status==='planning'||turn.plan?.clips?.some(clip=>['starting','running','saving'].includes(clip.status))||['starting','running','saving'].includes(turn.plan?.job?.status)||['queued','running','saving'].includes(turn.plan?.motion?.status));
    if(active&&conversation) pollTimer=setTimeout(async()=>{try {state=await api(conversation+'/refresh/',{}); render();} catch(error) {feedback(error.message,true); pollTimer=setTimeout(schedulePoll,10000);}},6000);
  }
  function lock(value) { sending=value;workbench.busy(value||actionBusy); byId('assistant-send').disabled=value||uploadBusy; byId('assistant-add').disabled=value||uploadBusy; byId('assistant-message').readOnly=value; for(const id of ['workflow','model','shape','priority','template','image-policy','max-cost']) byId('assistant-'+id).disabled=value||uploadBusy; renderAttachments();pickerMenus(); }
  async function runAction(plan, action, job_id=null, extra={}) {
    if(actionBusy||sending) return; actionBusy=true;workbench.busy(true); renderPlan(); feedback(action==='start'?'Startar den godkända generationen…':'Arbetar med din plan…');
    if(['preview','final'].includes(action))extra={render_key:crypto.randomUUID(),...extra};
    try { state=await api(conversation+'/action/',{plan_id:plan.id,expected_revision:state.revision,action,job_id,...extra}); render(); feedback(action==='edit_motion'?'En ny videoversion är sparad. Skapa och granska en ny förhandsvisning.':'Planen är uppdaterad.'); }
    catch(error) { feedback(error.message,true); try {state=await api(conversation+'/state/'); render();} catch {} }
    finally { actionBusy=false; renderPlan();workbench.busy(false); }
  }
  byId('assistant-composer').addEventListener('submit',async event=>{
    event.preventDefault(); if(sending||uploadBusy||actionBusy) return;
    const message=byId('assistant-message').value.trim(); if(!message) return;
    lock(true); feedback('Förbereder svar och plan…');
    try {
      if(!conversation) {const oldKey=storageKey();const data=await api('new/',{key:draftKey}); conversation=data.id; history.replaceState(null,'',base+conversation+'/');try{sessionStorage.removeItem(oldKey);}catch{}saveDraft();}
      const payload=pendingPayload||{key:draftKey,expected_revision:state.revision,message,workflow:byId('assistant-workflow').value,model:byId('assistant-model').value,shape:byId('assistant-shape').value,priority:byId('assistant-priority').value,template:byId('assistant-template').value,image_policy:byId('assistant-image-policy').value,max_cost_usd:byId('assistant-max-cost').value,attachments:attachments.map(({asset_id,role})=>({asset_id,role})),motion_source_render:byId('assistant-workflow').value==='motion'?motionSourceRender:null};
      pendingPayload=payload; state=await api(conversation+'/send/',payload); pendingPayload=null; draftKey=crypto.randomUUID();
      if(state.turns.at(-1)?.status!=='failed') {byId('assistant-message').value='';motionSourceRender=null;}
      saveDraft();
      render(); feedback(state.turns.at(-1)?.status==='failed'?state.turns.at(-1).error:'Planen är sparad. Du kan fortsätta med en ändring.',state.turns.at(-1)?.status==='failed');
    } catch(error) { feedback(error.message+' Din text finns kvar.',true); if(conversation) {try {state=await api(conversation+'/state/'); render(); if(state.turns.some(item=>item.id===draftKey&&item.status!=='planning')) {pendingPayload=null;draftKey=crypto.randomUUID();}} catch {}} }
    finally {lock(false); renderPlan();}
  });
  async function library(page=0) {
    const sequence=++libraryRequest; byId('assistant-library-status').textContent='Hämtar biblioteket…';
    try {const data=await api('assets/?q='+encodeURIComponent(byId('assistant-search').value)+'&page='+page); if(sequence!==libraryRequest)return;
      const grid=byId('assistant-library-grid'); if(page===0)grid.replaceChildren();
      for(const asset of data.assets) {const el=button('',()=>{try {addAsset(asset);} catch(error){byId('assistant-library-status').textContent=error.message;}}); if(asset.kind==='image') {const img=node('img');img.src=asset.url;img.alt='';img.loading='lazy';el.append(img);} else el.append(node('strong',asset.kind==='audio'?'Ljud':'Video'));el.append(node('span',asset.label));grid.append(el);}
      nextPage=data.next_page; byId('assistant-library-more').hidden=nextPage===null; byId('assistant-library-status').textContent=data.assets.length?'Välj en fil.':'Inga filer matchade sökningen.';
    } catch(error) {byId('assistant-library-status').textContent=error.message;}
  }
  async function upload(file, role=byId('assistant-file-role').value) {
    if(uploadBusy||sending)return; if(file.size>80*1024*1024) {feedback('Filen är för stor, högst 80 MB.',true);return;}
    uploadBusy=true; lock(sending); feedback('Laddar upp '+file.name+'…'); byId('assistant-library-status').textContent='Laddar upp…';
    try {const body=new FormData();body.append('file',file); const response=await fetch(base+'upload/',{method:'POST',body,credentials:'same-origin',headers:{'X-CSRFToken':csrf,'Accept':'application/json'}});const data=await response.json();if(!response.ok)throw Error(data.error||'Uppladdningen misslyckades.');addAsset(data,role);}
    catch(error) {feedback(error.message,true);byId('assistant-library-status').textContent=error.message;}
    finally {uploadBusy=false;lock(sending);byId('assistant-upload').value='';}
  }
  byId('assistant-add').addEventListener('click',()=>{byId('assistant-library').showModal();library();});
  byId('assistant-search').addEventListener('input',()=>{clearTimeout(searchTimer);searchTimer=setTimeout(()=>library(),300);});
  byId('assistant-library-more').addEventListener('click',()=>{if(nextPage!==null)library(nextPage);});
  byId('assistant-upload').multiple=true;byId('assistant-upload').addEventListener('change',async event=>{for(const file of Array.from(event.target.files))await upload(file);});
  const composer=byId('assistant-composer'); for(const name of ['dragenter','dragover']) composer.addEventListener(name,event=>{event.preventDefault();composer.classList.add('drag-over');});
  composer.addEventListener('dragleave',()=>composer.classList.remove('drag-over'));composer.addEventListener('drop',async event=>{event.preventDefault();composer.classList.remove('drag-over');if(sending)return;for(const file of event.dataTransfer.files)await upload(file,'reference');});
  for(const name of ['shape','max-cost'])byId('assistant-'+name).addEventListener('input',pickerMenus);
  byId('assistant-workflow').addEventListener('change',()=>{if(byId('assistant-workflow').value!=='motion'&&byId('assistant-model').value==='remotion')byId('assistant-model').value='';updateModels();});byId('assistant-model').addEventListener('change',()=>{
    if(byId('assistant-model').value==='remotion'){byId('assistant-workflow').value='motion';const template=catalog.templates.find(item=>item.id===byId('assistant-template').value);if(template&&!['motion','auto'].includes(template.kind))byId('assistant-template').value='';}
    else if(byId('assistant-workflow').value==='motion'){byId('assistant-workflow').value='auto';byId('assistant-template').value='';}
    updateModels();templateDescription();saveDraft();
  });byId('assistant-template').addEventListener('change',()=>{const template=catalog.templates.find(item=>item.id===byId('assistant-template').value);if(template&&template.kind!=='auto'){byId('assistant-workflow').value=template.kind;if(template.kind!=='motion'&&byId('assistant-model').value==='remotion')byId('assistant-model').value='';}updateModels();templateDescription();});
  for(const el of document.querySelectorAll('[data-example]'))el.addEventListener('click',()=>{byId('assistant-message').value=el.dataset.example;byId('assistant-workflow').value=el.dataset.workflow;if(el.dataset.template)byId('assistant-template').value=el.dataset.template;updateModels();templateDescription();saveDraft();byId('assistant-message').focus();});
  for(const el of document.querySelectorAll('[data-close-dialog]'))el.addEventListener('click',()=>el.closest('dialog').close());
  byId('assistant-manage-templates').addEventListener('click',()=>{updateTemplates();byId('assistant-template-dialog').showModal();});
  byId('template-existing').addEventListener('change',()=>{const item=catalog.templates.find(item=>item.id===byId('template-existing').value);byId('template-title').value=item?.title||'';byId('template-instructions').value=item?.instructions||'';byId('template-kind').value=item?.kind||'auto';});
  byId('assistant-template-form').addEventListener('submit',async event=>{event.preventDefault();const submit=event.target.querySelector('[type=submit]');submit.disabled=true;byId('template-status').textContent='Sparar…';
    try {const existing=catalog.templates.find(item=>item.id===byId('template-existing').value);const data=await api('templates/',{title:byId('template-title').value,instructions:byId('template-instructions').value,kind:byId('template-kind').value,key:existing?.key||''});catalog.templates=data.templates;updateTemplates();byId('template-status').textContent='En ny mallversion är sparad. Tidigare planer behåller sin mall.';}
    catch(error){byId('template-status').textContent=error.message;}finally{submit.disabled=false;}
  });
  for(const el of [...composer.querySelectorAll('textarea,select'),byId('assistant-max-cost'),byId('assistant-image-policy')])el.addEventListener('input',()=>{pendingPayload=null;draftKey=crypto.randomUUID();saveDraft();});
  byId('assistant-max-cost').addEventListener('input',renderPlan);
  for(const picker of document.querySelectorAll('.assistant-picker')){picker.addEventListener('toggle',()=>{if(!picker.open)return;for(const other of document.querySelectorAll('.assistant-picker'))if(other!==picker)other.open=false;const menu=picker.querySelector('.assistant-picker-menu');picker.classList.toggle('drop-up',menu.getBoundingClientRect().bottom>innerHeight-12);});picker.addEventListener('keydown',event=>{if(event.key==='Escape'){picker.open=false;picker.querySelector('summary').focus();}});}
  for(const el of document.querySelectorAll('.assistant-mobile-views button'))el.addEventListener('click',()=>{app.dataset.view=el.dataset.view;for(const item of document.querySelectorAll('.assistant-mobile-views button'))item.setAttribute('aria-pressed',String(item===el));if(el.dataset.view==='plan')byId('assistant-results-pane').querySelector('h2').focus();});
  updateModels();restoreChoices(state.turns.at(-1));
  try {const draft=JSON.parse(sessionStorage.getItem(storageKey())||'null');if(draft){motionSourceRender=draft.motionSourceRender||null;byId('assistant-message').value=draft.message||'';for(const [name,value] of Object.entries(draft.choices||{}))if(byId('assistant-'+name))byId('assistant-'+name).value=value;updateModels();attachments=draft.attachments||attachments;renderAttachments();templateDescription();}}catch{}
  render();
  if(matchMedia('(max-width:760px)').matches) document.querySelector('.assistant-projects details').open=false;
  // Never submit on Enter: multiline creative briefs and keyboard users need predictable editing.
}
