/* The workbench sends closed scene edits or a new chat turn, never renderer code. */
export function motionStudio({app,node,button,media,link,onAction,onComment}) {
  const root=document.getElementById('assistant-motion-studio');
  let signature='',locked=false,activeDraft='',selectedVersion='';
  const drafts=new Map();
  function captureDraft() {
    if(!activeDraft)return;
    const previous=drafts.get(activeDraft);
    drafts.set(activeDraft,{values:{...previous?.values,...Object.fromEntries([...root.querySelectorAll('input,textarea')].map(input=>[input.id,input.value]))},open:root.querySelector('details')?.open??previous?.open??false});
  }
  const time=value=>`${Math.floor(value/60).toString().padStart(2,'0')}:${(value%60).toFixed(2).padStart(5,'0')}`;
  function busy(value) {locked=value;for(const control of root.querySelectorAll('button,input,textarea,select'))control.disabled=value||control.dataset.readonly==='true';}
  function render(state) {
    const turn=[...state.turns].reverse().find(item=>item.plan?.motion);
    root.hidden=!turn;app.dataset.motion=String(Boolean(turn));
    if(!turn)return;
    const plan=turn.plan,motion=plan.motion,spec=motion.spec;
    const next=JSON.stringify({id:plan.id,current:plan.current,motion});
    if(next===signature)return;
    captureDraft();const draftId=plan.id+':'+motion.revision;if(activeDraft!==draftId)selectedVersion='';activeDraft=draftId;
    const draft=drafts.get(activeDraft);
    signature=next;root.replaceChildren();
    root.append(node('h2','Video och redigering'),node('p',`Remotion · videoversion ${motion.revision}`,'assistant-version'));
    const statuses={saved:'Projektet är sparat. Skapa en förhandsvisning.',queued:'Väntar på renderaren…',running:'Renderar videon…',saving:'Sparar videon…',completed:'Videon är klar.',failed:'Renderingen misslyckades.',canceled:'Renderingen avbröts.'};root.append(node('p',statuses[motion.status]||motion.status,'assistant-version'));
    if(!plan.current)root.append(node('p','En ny plan finns i chatten. Granska och förbered den för att uppdatera videon.','assistant-plan-notice'));
    if(!motion.available)root.append(node('p','Starta Motion-renderaren på din dator för att skapa förhandsvisningen.','assistant-plan-notice'));
    const outputs=[];
    for(const item of [...state.turns].reverse())for(const version of item.plan?.motion?.versions||[])outputs.push({...version,turn:item});
    const seen=new Set(),versions=outputs.filter(v=>!seen.has(v.id)&&seen.add(v.id));
    const playerSlot=node('div'),versionSelect=node('select');versionSelect.setAttribute('aria-label','Visa videoversion');
    let player=null,playing=null;
    const commentTime=node('p','','assistant-version');
    function showVersion(id) {
      selectedVersion=id;versionSelect.value=id||'';
      playing=versions.find(v=>v.id===id);playerSlot.replaceChildren();
      for(const control of root.querySelectorAll('[data-preview-approval]')){control.dataset.readonly=String(playing?.id!==plan.prepared.render_id);control.disabled=locked||control.dataset.readonly==='true';}
      if(!playing){playerSlot.append(node('p','Här visas videon när förhandsvisningen är klar.','assistant-placeholder'));return;}
      player=media(playing.output);player.setAttribute('aria-label','Remotion-video');
      player.addEventListener('timeupdate',()=>{commentTime.textContent='Kommentera vid '+time(player.currentTime);});
      playerSlot.append(player,node('p',`Visar plan ${playing.turn.revision}, videoversion ${playing.revision} · ${playing.mode==='final'?'färdig video':'förhandsvisning'}`,'assistant-version'),link('Öppna videofilen',playing.output.url));
      commentTime.textContent='Kommentera vid 00:00.00';
    }
    for(const version of versions){const opt=node('option',`Plan ${version.turn.revision} · v${version.revision} · ${version.mode==='final'?'färdig':'förhandsvisning'}`);opt.value=version.id;versionSelect.append(opt);}
    if(versions.length){versionSelect.addEventListener('change',()=>showVersion(versionSelect.value));root.append(versionSelect);}
    root.append(playerSlot);showVersion(versions.some(v=>v.id===selectedVersion)?selectedVersion:versions.find(v=>v.output.asset_id===motion.output?.asset_id)?.id||versions[0]?.id);
    const actions=node('div','','assistant-motion-actions');
    if(plan.current&&['saved','failed','canceled'].includes(motion.status))actions.append(button('Skapa ny förhandsvisning',()=>onAction(plan,'preview')));
    if(plan.current&&motion.status==='completed'&&motion.mode==='preview'){const approve=button(motion.approved?'Skapa färdig video':'Godkänn förhandsvisningen',()=>onAction(plan,motion.approved?'final':'approve_preview'));approve.dataset.previewApproval='true';approve.dataset.readonly=String(playing?.id!==plan.prepared.render_id);actions.append(approve);}
    if(plan.current&&['queued','running','saving'].includes(motion.status))actions.append(button('Avbryt renderingen',()=>onAction(plan,'cancel')));
    root.append(actions);
    if(motion.error)root.append(node('p',motion.error,'assistant-plan-notice'));
    if(spec&&plan.current&&motion.editable) {
      const editor=node('details');editor.open=draft?.open||false;editor.append(node('summary','Redigera text och tid per scen'));
      const form=node('form','','assistant-motion-editor'),fields=[];
      spec.scenes.forEach((scene,index)=>{
        const group=node('fieldset');group.append(node('legend',`${index+1}. ${scene.props.headline||'Scen'}`));
        const values={scene_id:scene.id};
        for(const [key,label,max] of [['headline','Rubrik',240],['body','Beskrivning',500],['cta','Uppmaning',100],['duration_seconds','Längd i sekunder',60]]) {
          const input=node(key==='body'?'textarea':'input');input.id=`motion-${scene.id}-${key}`;
          if(key==='duration_seconds'){input.type='number';input.min='0.5';input.max='60';input.step='0.01';input.value=(scene.duration_frames/spec.fps).toFixed(2);if(scene.component==='footage'){input.disabled=true;input.dataset.readonly='true';}}
          else{input.maxLength=max;input.value=scene.props[key]||'';}
          input.dataset.initial=input.value;
          if(draft?.values[input.id]!==undefined)input.value=draft.values[input.id];
          const name=node('label',label);name.htmlFor=input.id;group.append(name,input);values[key]=input;
        }
        fields.push(values);form.append(group);
      });
      form.append(node('p','Sparar en ny version. Bilder, logga, ljud och övriga sceneffekter behålls. Granska en ny förhandsvisning före färdig video.','assistant-model-note'));
      const save=button('Spara ny videoversion',()=>{});save.type='submit';form.append(save);
      const editKey=crypto.randomUUID();
      const editStatus=node('p');editStatus.setAttribute('role','status');form.append(editStatus);
      form.addEventListener('submit',event=>{event.preventDefault();if(locked)return;const edits=fields.map(row=>Object.fromEntries(Object.entries(row).filter(([key,input])=>key==='scene_id'||!input.disabled&&input.value!==input.dataset.initial).map(([key,input])=>[key,key==='scene_id'?input:input.value]))).filter(row=>Object.keys(row).length>1);if(!edits.length){editStatus.textContent='Ändra text eller tid innan du sparar en ny version.';return;}onAction(plan,'edit_motion',{edit_key:editKey,motion_revision:motion.revision,motion_edits:edits});});
      editor.append(form);root.append(editor);
    } else if(plan.current&&spec)root.append(node('p','Filmprojektets material och tider redigeras i filmsteget.','assistant-model-note'));
    if(plan.current) {
      const commentForm=node('form','','assistant-motion-comment');
      const comment=node('textarea');comment.id='motion-comment';comment.maxLength=5000;comment.required=true;comment.rows=3;comment.placeholder='Till exempel: gör rubriken kortare här och låt scenen ligga kvar två sekunder längre.';
      comment.value=draft?.values[comment.id]||'';
      const label=node('label','Kommentar till videon');label.htmlFor=comment.id;
      const submit=button('Skicka ändringsförslag',()=>{});submit.type='submit';submit.disabled=!versions.length;submit.dataset.readonly=String(!versions.length);
      commentForm.append(label,commentTime,comment,node('p','Pausa där du vill ändra. Kommentaren skickas till chatten som ett förslag. Du granskar nästa version innan rendering.','assistant-model-note'),submit);
      commentForm.addEventListener('submit',event=>{event.preventDefault();if(locked||!player||!playing)return;player.pause();onComment(playing.turn,`Ändringskommentar till plan ${playing.turn.revision}, videoversion ${playing.revision}, vid ${time(player.currentTime)}: ${comment.value.trim()}\nBevara alla andra scener och allt övrigt material.`,playing.id);});
      root.append(commentForm);
    }
    if(plan.prepared.url)root.append(link('Öppna hela Motion-projektet',plan.prepared.finish_url||plan.prepared.url));
    busy(locked);
  }
  return {render,busy};
}
