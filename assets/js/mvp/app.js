(function(global){
  var app = global.DeepDemandMvp = global.DeepDemandMvp || {};

  var initialReportState = {
    origText: document.querySelector('.orig-text') ? document.querySelector('.orig-text').textContent : '',
    newSentence: document.querySelector('.newreq-sentence') ? document.querySelector('.newreq-sentence').textContent : '',
    detailBody: document.querySelector('.detail-body') ? document.querySelector('.detail-body').textContent : '',
    sugFocusHtml: document.querySelector('.sug-focus') ? document.querySelector('.sug-focus').innerHTML : '',
    sugActHtml: document.querySelector('.sug-act') ? document.querySelector('.sug-act').innerHTML : '',
    roadmapHtml: document.querySelector('.linear-roadmap') ? document.querySelector('.linear-roadmap').innerHTML : '',
    flowHtml: document.querySelector('.flow') ? document.querySelector('.flow').innerHTML : '',
    whyHtml: getBodyValHtmlByTag('t-why'),
    whatHtml: getBodyValHtmlByTag('t-what'),
    whereHtml: getBodyValHtmlByTag('t-wheren'),
    whoHtml: getBodyValHtmlByTag('t-who'),
    howHtml: getBodyValHtmlByTag('t-how'),
    howmuchHtml: getBodyValHtmlByTag('t-howmuch'),
    inputHtml: getBodyValHtmlByTag('t-input'),
    outputHtml: getBodyValHtmlByTag('t-output'),
    monitorHtml: getBodyValHtmlByTag('t-monitor')
  };

  var mvpState = {
    original: '',
    analysis: null,
    card: null,
    selectedOptions: {
      affected_roles: [],
      focus_points: [],
      system_expectations: [],
      scenario_answers: {}
    },
    fastAnalysisStatus: 'idle',
    deepAnalysisStatus: 'idle',
    deepAnalysis: null
  };
  var aiPopupTimer = null;

  function getBodyValHtmlByTag(tagClass){
    var tag = document.querySelector('.body-tag.' + tagClass);
    var item = tag ? tag.closest('.body-item') : null;
    var val = item ? item.querySelector('.body-val') : null;
    return val ? val.innerHTML : '';
  }

  function showMvpStatus(message){
    var el = document.getElementById('mvpStatus');
    if(!el) return;
    el.textContent = message;
    el.classList.add('show');
  }

  function ensureAiPopup(){
    var popup = document.getElementById('mvpAiPopup');

    if(popup) return popup;

    popup = document.createElement('div');
    popup.id = 'mvpAiPopup';
    popup.className = 'mvp-ai-popup';
    popup.setAttribute('role', 'status');
    popup.setAttribute('aria-live', 'polite');
    popup.innerHTML =
      '<div class="mvp-ai-popup-card">' +
        '<button type="button" class="mvp-ai-popup-close" aria-label="????">?</button>' +
        '<div class="mvp-ai-popup-row">' +
          '<div class="mvp-ai-popup-icon"></div>' +
          '<div>' +
            '<div id="mvpAiPopupTitle" class="mvp-ai-popup-title"></div>' +
            '<div id="mvpAiPopupText" class="mvp-ai-popup-text"></div>' +
          '</div>' +
        '</div>' +
      '</div>';

    popup.querySelector('.mvp-ai-popup-close').addEventListener('click', hideAiPopup);
    document.body.appendChild(popup);
    return popup;
  }

  function hideAiPopup(){
    var popup = document.getElementById('mvpAiPopup');
    if(aiPopupTimer){
      clearTimeout(aiPopupTimer);
      aiPopupTimer = null;
    }
    if(popup){
      popup.classList.remove('show', 'thinking', 'success');
    }
  }

  function showAiPopup(type, title, message, autoCloseMs){
    var popup = ensureAiPopup();
    var closeBtn = popup.querySelector('.mvp-ai-popup-close');
    var titleEl = document.getElementById('mvpAiPopupTitle');
    var textEl = document.getElementById('mvpAiPopupText');

    if(aiPopupTimer){
      clearTimeout(aiPopupTimer);
      aiPopupTimer = null;
    }

    popup.classList.remove('thinking', 'success', 'error');
    popup.classList.add('show', type || 'thinking');
    if(titleEl) titleEl.textContent = title || '';
    if(textEl) textEl.textContent = message || '';
    if(closeBtn) closeBtn.style.display = type === 'thinking' ? 'none' : '';

    if(autoCloseMs){
      aiPopupTimer = setTimeout(hideAiPopup, autoCloseMs);
    }
  }

  function showAiThinking(message){
    showAiPopup('thinking', 'AI ?????', message || 'AI ????????????????');
  }

  function showAiSuccess(message){
    showAiPopup('success', '????', message || 'AI ????????????', 2600);
  }

  function showAiError(message){
    showAiPopup('error', '?????', message || 'AI ???????????', 3200);
  }

  function setButtonLoading(buttonId, isLoading, loadingText){
    var btn = document.getElementById(buttonId);
    if(!btn) return;
    if(isLoading){
      btn.dataset.originalText = btn.dataset.originalText || btn.textContent;
      btn.textContent = loadingText || '???...';
      btn.disabled = true;
      btn.classList.add('loading');
      return;
    }
    btn.textContent = btn.dataset.originalText || btn.textContent;
    btn.disabled = false;
    btn.classList.remove('loading');
  }

  function renderCardLoading(message){
    var panel = document.getElementById('mvp-card-panel');
    var box = document.getElementById('demandCard');
    if(panel) panel.style.display = '';
    if(box){
      box.innerHTML = '<div class="mvp-result-brief"><div class="mvp-result-label">' + escapeHtml(message || 'AI????????...') + '</div><div class="mvp-result-text">?????????????????</div></div>';
    }
  }

  function setDeepAnalysisStatus(status, message){
    var statusEl = document.getElementById('deepAnalysisStatus');
    var button = document.getElementById('deepAnalysisBtn');
    mvpState.deepAnalysisStatus = status || 'idle';
    if(statusEl){
      statusEl.textContent = message || '';
      statusEl.className = 'mvp-deep-status ' + mvpState.deepAnalysisStatus;
    }
    if(button){
      button.disabled = mvpState.deepAnalysisStatus === 'loading' || !mvpState.analysis;
      button.textContent = mvpState.deepAnalysisStatus === 'loading' ? '???...' : '?? ITBP ????';
    }
  }

  function updateFrontReportFromCard(card){
    // ????????????????????? ITBP ?????
    updateSolutionSummary();
  }

  function updateHomeDemandPreview(card){
    var preview = document.getElementById('homeDemandPreview');
    if(!preview || !card) return;

    setTextById('homePreviewOriginal', card.original_request || mvpState.original || '???');
    setTextById('homePreviewRefined', card.refined_request || card.rewritten_request || app.summarizeSentence(card) || '???');
    setTextById('homePreviewPending', card.pending_questions || '?????????');
    preview.classList.add('show');
  }

  function setHtmlById(id, html){
    var el = document.getElementById(id);
    if(el) el.innerHTML = html;
  }

  function setTextById(id, text){
    var el = document.getElementById(id);
    if(el) el.textContent = text;
  }

  function getCurrentSolutionCard(){
    return mvpState.card || (mvpState.analysis ? buildCardFromState() : null);
  }

  function updateSolutionSummary(){
    var card = getCurrentSolutionCard();
    var analysis = mvpState.analysis || {};
    if(!document.getElementById('solutionOriginalRequest')) return;

    setTextById('solutionOriginalRequest', card ? (card.original_request || mvpState.original || '???') : '????????????????? AI ???');
    setTextById('solutionRefinedRequest', card ? (card.refined_request || card.rewritten_request || '???') : '???');
    setTextById('solutionDomainObject', card ? ((analysis.businessDomain || card.domain_name || '???') + ' / ' + ((analysis.businessObject || (card.diagnosis && card.diagnosis.business_object)) || '???????')) : '???');
    setTextById('solutionPendingQuestions', card ? (card.pending_questions || (analysis.uncertainItems || []).join('?') || '????????') : '???');
  }

  function listHtml(items){
    return (items || []).map(function(item){ return '<li>' + escapeHtml(item) + '</li>'; }).join('');
  }

  function buildSolutionDraft(card){
    var analysis = mvpState.analysis || {};
    var domain = String(analysis.businessDomain || card.domain_name || '');
    var text = [
      card.original_request,
      card.refined_request,
      card.rewritten_request,
      domain,
      analysis.businessObject,
      (analysis.painPoints || []).join(' ')
    ].join(' ');
    var isInventory = /??|??|??|??|??/.test(text);
    var isBom = /BOM|??|??|??|??/.test(text);
    var isOrder = /??|??|??|???|???|??/.test(text);

    if(isInventory){
      return {
        summary: '???????????????????????????????????????????????????????????????????????',
        entry: '?????? / ????????',
        systems: 'WMS???ERP/SAP???????????????????',
        modules: ['?????????', '???????????', '??????', '????????', '????????????', '???????????'],
        stages: [
          ['??1', '???????????????????'],
          ['??2', '?? WMS/ERP ??????????????'],
          ['??3', '??????????????????'],
          ['??4', '???????????????????']
        ],
        risks: ['?????????????????????', 'WMS ? ERP ??????????????', '????????????????????????', '??????????????????']
      };
    }
    if(isBom){
      return {
        summary: '?????BOM/?????????????????????????????????????????????????????????????',
        entry: 'BOM/??????????',
        systems: 'PLM?ERP/SAP???????????????',
        modules: ['????????', '????????', '???????', '??/??????', '???????', '????????'],
        stages: [
          ['??1', '???????????????'],
          ['??2', '?? PLM?ERP?????????????'],
          ['??3', '?????????????????'],
          ['??4', '???????????????']
        ],
        risks: ['BOM???????????????????????', '???BOM?????????????????', '????????????????????']
      };
    }
    if(isOrder){
      return {
        summary: '?????????????????????????????????????????????????????????????????????',
        entry: '???? / ?????????',
        systems: '?????ERP/SAP?WMS?MES/?????????',
        modules: ['?????????', '?????????', '??/????', '???????', '????????', '??????'],
        stages: [
          ['??1', '??????????????'],
          ['??2', '????????????????'],
          ['??3', '?????????????????'],
          ['??4', '?????????????????????']
        ],
        risks: ['??????????????????????', '????????????????????', '??????????????????']
      };
    }
    return {
      summary: '??????????????????????????????????????????????????????????????',
      entry: '????????',
      systems: '???????????????????????',
      modules: ['????????', '???????', '?????', '??????', '??????'],
      stages: [
        ['??1', '?????????????????'],
        ['??2', '??????????????'],
        ['??3', '????????????'],
        ['??4', '??????????????']
      ],
      risks: ['??????????????', '????????????????', '??????????????????']
    };
  }

  function renderSolutionDraft(draft){
    draft = normalizeSolutionDraft(draft);
    setTextById('solutionExecutiveSummary', draft.summary);
    setTextById('solutionEntryPoint', draft.entry);
    setTextById('solutionDataSystems', draft.systems);
    setHtmlById('solutionModules', listHtml(draft.modules));
    setHtmlById('solutionRisks', listHtml(draft.risks));
    setHtmlById('solutionStages', draft.stages.map(function(stage){
      return '<div class="solution-stage"><b>' + escapeHtml(stage[0]) + '</b><span>' + escapeHtml(stage[1]) + '</span></div>';
    }).join(''));
  }

  function normalizeSolutionDraft(raw){
    var draft = raw || {};
    var stages = Array.isArray(draft.stages) ? draft.stages : [];
    return {
      summary: String(draft.executive_summary || draft.summary || '????????'),
      entry: String(draft.entry_point || draft.entry || '????????'),
      systems: String(draft.data_systems || draft.systems || '??????????'),
      modules: normalizeArray(draft.modules).length ? normalizeArray(draft.modules) : ['????????', '????', '?????', '????'],
      risks: normalizeArray(draft.risks).length ? normalizeArray(draft.risks) : normalizeArray(draft.confirmations),
      stages: stages.map(function(stage, index){
        if(Array.isArray(stage)){
          return [String(stage[0] || ('??' + (index + 1))), String(stage[1] || '')];
        }
        return [String((stage && stage.name) || ('??' + (index + 1))), String((stage && stage.description) || '')];
      }).filter(function(stage){ return stage[0] || stage[1]; })
    };
  }

  function markdownList(items, fallback){
    var list = normalizeArray(items);
    if(!list.length && fallback) list = [fallback];
    return list.map(function(item){ return '- ' + item; }).join('\n');
  }

  function inferPrdScenario(text){
    text = String(text || '');
    if(/??|??|??|??|??|??|??|??|8D|NCR|CAPA|??|???|??|??/.test(text)) return 'quality_control';
    if(/??|????|??|??|??|MES|??|??|??|??|??|????|??/.test(text)) return 'manufacturing_execution';
    if(/??|???|??|??|??|????|PO|????|??|??|??/.test(text)) return 'procurement_delivery';
    if(/????|??|????|????|??|??|???|????|????/.test(text)) return 'plan_material_shortage';
    if(/BOM|??|??|??|??|???|ECN|ECR/.test(text)) return 'bom_change';
    if(/??|??|??|???|???|??|??|????/.test(text)) return 'order_delivery';
    if(/??|??|??|????|??|??|??|WMS/.test(text)) return 'inventory_check';
    if(/???|?????|?????|??????|??|??|??|????/.test(text)) return 'master_data';
    return 'generic';
  }

  function uniquePrdList(items){
    var seen = {};
    return normalizeArray(items).map(function(item){ return String(item || '').trim(); }).filter(function(item){
      if(!item || seen[item]) return false;
      seen[item] = true;
      return true;
    });
  }

  function makeFunctionRows(modules, pack){
    var source = uniquePrdList(modules).length ? uniquePrdList(modules) : pack.defaultModules;
    return source.slice(0, 8).map(function(moduleName, index){
      var detail = (pack.moduleRules && pack.moduleRules[moduleName]) || [
        '???' + pack.trigger + '?',
        '???' + pack.inputs.slice(0, 3).join('?') + '?',
        '????' + pack.objectName + '????????????????',
        '???' + pack.outputs.slice(0, 2).join('?') + '?'
      ].join('');
      return ['F' + String(index + 1).padStart(2, '0'), moduleName, detail, index < 3 ? 'P0' : 'P1'];
    });
  }

  function prdDomainPack(scenario, ctx){
    var packs = {
      quality_control: {
        title: '??????????? PRD',
        objectName: '????',
        trigger: '????????????????????/??',
        roles: ['?????', '???', '?????', '????????', 'ITBP'],
        inputs: ['????', '??/????', '??/???', '????', '????', '????', '????', '????', '??/??', '????'],
        outputs: ['?????', '????', '?????', '??/??/??/????', 'CAPA/8D ????'],
        defaultModules: ['??????', '?????????', '?????', '??????', 'CAPA/8D ??', '???????'],
        moduleRules: {
          '??????': '?????????????????????????????????????????????????????',
          '?????????': '?????????????????????????????????????',
          '?????': '??????????????????????????????????????',
          '??????': '???????????????????????????????????',
          'CAPA/8D ??': '???????????? CAPA/8D ??????????????????????????'
        },
        scopeOut: ['????????????????', '????? CAPA/8D??????????', '??????????????????'],
        businessFlow: ['?????????????????', '?????????????????????', '??????????????????', '??????????????? CAPA/8D?', '?????????????????'],
        implementationPlan: ['????????????????????????', '???????????????????????', '????????????????????', '???????????????????'],
        exceptions: ['????????????????????????', '??????????????????????', '???????????????????????', '??????????????????'],
        nonFunctional: ['?????????/???????????????????', '???????????CAPA??????????', '??????????????????', '???????????????????'],
        acceptance: ['???????????????????????????????', '???????????????????????????', '??????? CAPA/8D ??????????????', '???????????????????????'],
        confirmations: ['??????????????????????', '???????? CAPA/8D?', '????????????', '???????????????????']
      },
      manufacturing_execution: {
        title: '????????????? PRD', objectName: '??????', trigger: '?????????????????????', roles: ['???', '?????', '?????', '?????', '????'],
        inputs: ['???', '??', '??', '??', '????', '????', '????', '????', '????', '???'], outputs: ['?????', '??/????', '?????', '????', '??????'],
        defaultModules: ['??????', '??????', '??????', '?????', '??????', '????'], scopeOut: ['????????????', '??? MES/?????????', '??????????'],
        businessFlow: ['??????????????', '???????????????????', '??????????????????????????', '???????????????????', '??????????????'], implementationPlan: ['????????????????', '??????????????????', '??????????????????', '??????????????'],
        exceptions: ['???????????????', '??????????????????', '?????????????'], nonFunctional: ['????????????????????', '????????????????', '?????????????????'], acceptance: ['????????????????', '?????????????????', '??????????????'], confirmations: ['????????????', '??????????????', '???????????']
      },
      procurement_delivery: {
        title: '????????????? PRD', objectName: '??????', trigger: '????????????????????????????', roles: ['???', '?????', '???', '??', '????'],
        inputs: ['?????', '????', '???', '????', '????', '????', '????', '????', '???', '???'], outputs: ['??????', '????', '???????', '??????', '????'],
        defaultModules: ['????????', '??????', '????', '???????', '??????', '??????'], scopeOut: ['??????????', '???????????', '?????????????'],
        businessFlow: ['?????????????????????', '?????????????????????????', '????????????????', '??????????????', '???????????/?????'], implementationPlan: ['???????????????', '??????????????????', '?????????????????', '?????????????'],
        exceptions: ['????????????????', '???????????????????????', '??????????????'], nonFunctional: ['?????????????????????????', '??????????????????', '???????????????'], acceptance: ['PO ????????????????', '????????????????????', '????????????????'], confirmations: ['??????????? MRP ???', '???????????????', '??????????']
      },
      order_delivery: {
        title: '?????????????? PRD', objectName: '????', trigger: '??????????????????', roles: ['??', '??', '??', '??', '??'],
        inputs: ['???', '??', '??', '????', '????', '????', '????', '????'], outputs: ['??????', '??????', '??????', '?????'], defaultModules: ['??????', '??????', '??????', '?????', '??????'], scopeOut: ['?????????', '???????????????'], businessFlow: ['???????', '??????????????????', '????????????', '?????????????????'], implementationPlan: ['??????????', '?????????????', '??????????', '?????????'], exceptions: ['???????????????', '?????????????'], nonFunctional: ['??????????', '??????????????????'], acceptance: ['????????????', '????????????', '????????????'], confirmations: ['????????????', '?????????', '???????????']
      },
      inventory_check: {
        title: '???????????? PRD', objectName: '?????', trigger: '??????????????????', roles: ['??', '??', '??', '???', '??'], inputs: ['????', '??', '??', '????', '????', '????', '????', '??'], outputs: ['??????', '????', '??????', '????'], defaultModules: ['??????', '??/????', '??????', '??????', '????'], scopeOut: ['?????????', '??????????'], businessFlow: ['???????????', '??????????????????', '???????????????', '??????????'], implementationPlan: ['?????????', '?? ERP/WMS ?????', '??????????', '??????????'], exceptions: ['?????????????', '?????????????????'], nonFunctional: ['???????????????', '???/???????'], acceptance: ['????????????', '????????????', '????????'], confirmations: ['??????????', '?????? ERP ?? WMS?', '??????????']
      },
      master_data: {
        title: '????????????? PRD', objectName: '???', trigger: '??????????????????????', roles: ['?????', '?????', 'ITBP', '?????'], inputs: ['????', '???', '????', '????', '????', '????'], outputs: ['???????', '??????', '??????', '??????'], defaultModules: ['???????', '??????', '????', '??????', '????'], scopeOut: ['??????????', '???????????'], businessFlow: ['?????????', '?????????????????', '??????????', '???????????'], implementationPlan: ['?????????????', '???????????', '????????????', '????????????'], exceptions: ['???????????????', '???????????????'], nonFunctional: ['?????????', '????????????'], acceptance: ['?????????', '??????????????', '????????'], confirmations: ['?????????????', '?????????', '?????????']
      }
    };
    return packs[scenario] || {
      title: (ctx.businessObject || '????') + ' PRD', objectName: ctx.businessObject || '????', trigger: '???????????', roles: ['????','???','ITBP','?????'], inputs: ['????','????','??','???','????'], outputs: ['????','????','?????','????'], defaultModules: ['????', '????', '????', '?????', '????'], scopeOut: ['??????????', '????????????????'], businessFlow: ['?????????', '??????????????', '???????????????', '?????????'], implementationPlan: ['?????????????', '??????????', '?????????', '???????????'], exceptions: ['??????????', '????????????', '????????????'], nonFunctional: ['????????', '????????????', '??????????'], acceptance: ['?????????????????', '????????????????', '????????????'], confirmations: ctx.pendingList.length ? ctx.pendingList : ['????????', '????????????', '????????']
    };
  }

  function prdSpecForScenario(scenario, ctx){
    var pack = prdDomainPack(scenario, ctx);
    var functions = makeFunctionRows(ctx.modules, pack);
    var scopeIn = uniquePrdList(ctx.modules).length ? uniquePrdList(ctx.modules) : uniquePrdList(pack.defaultModules);
    return {
      title: pack.title,
      objectives: [
        '?' + pack.trigger + '???????' + pack.objectName + '???????????????',
        '??' + pack.outputs.slice(0, 3).join('?') + '??' + pack.roles.slice(0, 3).join('?') + '?????????',
        '????????????????????????????????????'
      ],
      scopeIn: scopeIn.map(function(item){ return '??' + item + '?????????????????????????????'; }),
      scopeOut: pack.scopeOut,
      businessFlow: pack.businessFlow,
      implementationPlan: pack.implementationPlan,
      functions: functions,
      dataRows: pack.inputs.slice(0, 8).map(function(item, index){ return [index === 0 ? pack.objectName + '???' : '????' + index, item, '????/??????']; }).concat(pack.outputs.slice(0, 5).map(function(item){ return ['????', item, '????????']; })),
      exceptions: pack.exceptions,
      nonFunctional: pack.nonFunctional,
      acceptance: pack.acceptance,
      confirmations: uniquePrdList((ctx.pendingList || []).concat(pack.confirmations || []))
    };
  }
  function buildPrdMarkdown(card, draft){
    card = card || {};
    draft = normalizeSolutionDraft(draft);
    var analysis = mvpState.analysis || {};
    var report = card.structured_report || analysis.structuredReport || {};
    var textForScenario = [card.original_request, card.refined_request, card.rewritten_request, draft.summary, draft.systems, normalizeArray(draft.modules).join(' ')].join(' ');
    var pending = card.pending_questions || normalizeArray(analysis.uncertainItems).join('?') || '';
    var ctx = {
      businessObject: analysis.businessObject || (card.diagnosis && card.diagnosis.business_object) || report.what || '????',
      modules: normalizeArray(draft.modules),
      pendingList: pending ? pending.split(/[?;\n]/).map(function(item){ return item.trim(); }).filter(Boolean) : []
    };
    var spec = prdSpecForScenario(inferPrdScenario(textForScenario), ctx);
    var today = new Date().toISOString().slice(0, 10);
    var refined = card.refined_request || card.rewritten_request || analysis.rewrittenRequest || analysis.suggestedRequest || card.original_request || mvpState.original || '???';
    var original = card.original_request || mvpState.original || '???';
    var targetUsers = card.target_user || report.who || normalizeArray(analysis.targetUsers).join('?') || '???';
    var domain = [analysis.businessDomain || card.domain_name, analysis.businessObject || (card.diagnosis && card.diagnosis.business_object)].filter(Boolean).join(' / ') || '???';

    return [
      '# ' + spec.title,
      '',
      '## 1. ????',
      '',
      '| ?? | ?? |',
      '| --- | --- |',
      '| ???? | PRD ???????? |',
      '| ???? | ' + today + ' |',
      '| ???? | ' + (collectSolutionSettings().output_style || 'ITBP ?????') + ' |',
      '| ??? / ?? | ' + domain + ' |',
      '| ???? | AI ?????????ITBP?????????? |',
      '',
      '## 2. ????',
      '',
      original,
      '',
      '## 3. AI ??????',
      '',
      refined,
      '',
      '## 4. ??????',
      '',
      markdownList(normalizeArray(analysis.painPoints), report.why || '???????????????????????????'),
      '',
      '## 5. ????',
      '',
      markdownList(spec.objectives),
      '',
      '## 6. ???????',
      '',
      '- ?????' + targetUsers,
      '- ??/???????????????????????',
      '- ITBP????????????????????????',
      '- ??/????????????????????????',
      '',
      '## 7. ????',
      '',
      '### 7.1 ????',
      '',
      markdownList(spec.scopeIn),
      '',
      '### 7.2 ??????',
      '',
      markdownList(spec.scopeOut),
      '',
      '## 8. ????',
      '',
      '| ?? | ???? | ???? / ?? / ?? | ??? |',
      '| --- | --- | --- | --- |',
      spec.functions.map(function(row){ return '| ' + row[0] + ' | ' + row[1] + ' | ' + row[2] + ' | ' + row[3] + ' |'; }).join('\n'),
      '',
      '## 9. ??????',
      '',
      spec.businessFlow.map(function(step, index){ return (index + 1) + '. ' + step; }).join('\n'),
      '',
      '## 10. ???????',
      '',
      '| ???? | ???? / ?? | ?? / ?? |',
      '| --- | --- | --- |',
      spec.dataRows.map(function(row){ return '| ' + row[0] + ' | ' + row[1] + ' | ' + row[2] + ' |'; }).join('\n'),
      '',
      '## 11. ?????',
      '',
      '- ???????????????????????????????',
      '- ??????????????????????????????',
      '- ITBP??? PRD ??????????????????',
      '- ???????????????????????????????????',
      '',
      '## 12. ????',
      '',
      markdownList(spec.exceptions),
      '',
      '## 13. ?????',
      '',
      markdownList(spec.nonFunctional),
      '',
      '## 14. ????',
      '',
      markdownList(spec.acceptance),
      '',
      '## 15. ???????',
      '',
      spec.implementationPlan.map(function(step, index){ return (index + 1) + '. ' + step; }).join('\n'),
      '',
      '## 16. ?????',
      '',
      markdownList(spec.confirmations),
      '',
      '## 17. ??',
      '',
      '- ? 9 ??????????? 15 ???????????????????',
      '- ? 12 ????????????????? 16 ?????/??????????????',
      '- ? PRD ? AI ?????????????????????????????????????????'
    ].join('\n');
  }
  function renderMarkdownAsPrdHtml(markdown){
    var lines = String(markdown || '').split(/\r?\n/);
    var html = [];
    var inUl = false;
    var inOl = false;
    var inTable = false;
    var tableRows = [];

    function closeLists(){
      if(inUl){ html.push('</ul>'); inUl = false; }
      if(inOl){ html.push('</ol>'); inOl = false; }
    }
    function flushTable(){
      if(!inTable) return;
      closeLists();
      html.push('<table class="prd-table">' + tableRows.join('') + '</table>');
      tableRows = [];
      inTable = false;
    }
    function inline(text){
      return escapeHtml(text).replace(/\*\*(.*?)\*\*/g, '<b>$1</b>');
    }

    lines.forEach(function(line){
      var trimmed = line.trim();
      if(!trimmed){ flushTable(); closeLists(); return; }
      if(/^\|.*\|$/.test(trimmed)){
        if(trimmed.indexOf('---') > -1) return;
        inTable = true;
        var cells = trimmed.split('|').slice(1, -1).map(function(cell){ return inline(cell.trim()); });
        var tag = tableRows.length === 0 ? 'th' : 'td';
        tableRows.push('<tr>' + cells.map(function(cell){ return '<' + tag + '>' + cell + '</' + tag + '>'; }).join('') + '</tr>');
        return;
      }
      flushTable();
      if(trimmed.indexOf('# ') === 0){ closeLists(); html.push('<h1>' + inline(trimmed.slice(2)) + '</h1>'); return; }
      if(trimmed.indexOf('## ') === 0){ closeLists(); html.push('<h2>' + inline(trimmed.slice(3)) + '</h2>'); return; }
      if(trimmed.indexOf('### ') === 0){ closeLists(); html.push('<h3>' + inline(trimmed.slice(4)) + '</h3>'); return; }
      if(trimmed.indexOf('- ') === 0){
        if(!inUl){ closeLists(); html.push('<ul>'); inUl = true; }
        html.push('<li>' + inline(trimmed.slice(2)) + '</li>');
        return;
      }
      if(/^\d+\.\s+/.test(trimmed)){
        if(!inOl){ closeLists(); html.push('<ol>'); inOl = true; }
        html.push('<li>' + inline(trimmed.replace(/^\d+\.\s+/, '')) + '</li>');
        return;
      }
      closeLists();
      html.push('<p>' + inline(trimmed) + '</p>');
    });
    flushTable();
    closeLists();
    return html.join('');
  }

  function renderPrdDocument(draft){
    var card = getCurrentSolutionCard();
    if(!card) return;
    var markdown = buildPrdMarkdown(card, draft);
    var panel = document.getElementById('prdPanel');
    var doc = document.getElementById('prdDocument');
    mvpState.prdMarkdown = markdown;
    if(doc) doc.innerHTML = renderMarkdownAsPrdHtml(markdown);
    if(panel) panel.classList.add('show');
  }

  function downloadPrdDocument(){
    var markdown = mvpState.prdMarkdown;
    var downloadBtn = document.querySelector('.prd-actions .solution-btn.primary');
    if(!markdown){
      alert('???? PRD ???');
      return;
    }
    if(downloadBtn){
      downloadBtn.dataset.originalText = downloadBtn.dataset.originalText || downloadBtn.textContent;
      downloadBtn.textContent = '??????...';
      downloadBtn.disabled = true;
      downloadBtn.classList.add('loading');
    }
    try{
      var title = (markdown.split('\n')[0] || 'PRD??').replace(/^#\s*/, '').replace(/[\\/:*?"<>|]/g, '_');
      var html = '<!doctype html><html><head><meta charset="utf-8"><title>' + escapeHtml(title) + '</title>' +
        '<style>body{font-family:Microsoft YaHei,Arial,sans-serif;line-height:1.75;color:#1f2937;padding:28px}h1{font-size:24px}h2{font-size:18px;color:#0176d3;border-bottom:1px solid #ddd;padding-bottom:6px}table{border-collapse:collapse;width:100%;margin:10px 0}th,td{border:1px solid #ddd;padding:8px;text-align:left;vertical-align:top}th{background:#f5f7fb}</style>' +
        '</head><body>' + renderMarkdownAsPrdHtml(markdown) + '</body></html>';
      var blob = new Blob(['\ufeff' + html], { type: 'application/msword;charset=utf-8' });
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url;
      a.download = title + '.doc';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      showAiSuccess('PRD Word ????????');
    }finally{
      if(downloadBtn){
        downloadBtn.textContent = downloadBtn.dataset.originalText || '?? Word (.doc)';
        downloadBtn.disabled = false;
        downloadBtn.classList.remove('loading');
      }
    }
  }

  async function copyPrdMarkdown(){
    var markdown = mvpState.prdMarkdown;
    if(!markdown){
      alert('???? PRD ???');
      return;
    }
    try{
      await navigator.clipboard.writeText(markdown);
      showAiSuccess('PRD Markdown ??????????????????');
    }catch(error){
      alert('?????????????');
    }
  }
  function collectSolutionSettings(){
    var depth = document.getElementById('solutionDepth');
    var type = document.getElementById('solutionType');
    var style = document.getElementById('solutionStyle');
    var webSearch = document.getElementById('solutionWebSearch');
    return {
      depth: depth ? depth.value : '????',
      solution_type: type ? type.value : '????',
      output_style: style ? style.value : 'ITBP ?????',
      web_search: !!(webSearch && webSearch.checked)
    };
  }

  async function generateSolutionDraft(){
    var card = getCurrentSolutionCard();
    var status = document.getElementById('solutionStatus');
    var empty = document.getElementById('solutionEmpty');
    var output = document.getElementById('solutionOutput');
    var btn = document.getElementById('generateSolutionBtn');
    var rawResult;

    updateSolutionSummary();
    if(!card){
      alert('????????????????? AI ???');
      switchAppView('submission');
      return;
    }

    if(status){
      status.textContent = '???';
      status.className = 'solution-status generating';
    }
    if(output){
      output.classList.remove('show');
      output.classList.add('loading-placeholder');
    }
    var prdPanel = document.getElementById('prdPanel');
    if(prdPanel){
      prdPanel.classList.add('loading-placeholder');
    }
    if(btn){
      btn.dataset.originalText = btn.dataset.originalText || btn.textContent;
      btn.textContent = 'AI ???? PRD...';
      btn.disabled = true;
      btn.classList.add('loading');
    }
    showAiThinking('AI ?????????????? ITBP ???? PRD ???????');

    try{
      rawResult = await postJson('/api/generate_solution', {
        user_input: card.original_request || mvpState.original,
        analysis_result: serializeFastAnalysisForApi(),
        deep_analysis: mvpState.deepAnalysis || {},
        selected_options: Object.assign({}, mvpState.selectedOptions, {
          scenario_answers: collectScenarioAnswers()
        }),
        settings: collectSolutionSettings()
      });
    }catch(error){
      rawResult = buildSolutionDraft(card);
      rawResult.error_message = error.message;
    }

    renderSolutionDraft(rawResult);
    renderPrdDocument(rawResult);
    if(empty) empty.style.display = 'none';
    if(output){
      output.classList.remove('loading-placeholder');
      output.classList.add('show');
    }
    var generatedPrdPanel = document.getElementById('prdPanel');
    if(generatedPrdPanel){
      generatedPrdPanel.classList.remove('loading-placeholder');
    }
    if(status){
      status.textContent = rawResult.mode === 'llm' ? '??? PRD' : '??? PRD ??';
      status.className = 'solution-status ready';
    }
    if(btn){
      btn.textContent = btn.dataset.originalText || '?? PRD ??';
      btn.disabled = false;
      btn.classList.remove('loading');
    }
    showAiSuccess('PRD ???????????????????');
  }

  function setDeepSectionsPlaceholder(message){
    var text = message || '?????????????????????ITBP???????????';
    updateBodyValByTag('t-why', escapeHtml(text));
    updateBodyValByTag('t-what', '<span class="what-red">???</span>');
    updateBodyValByTag('t-wheren', '<b>???</b>');
    updateBodyValByTag('t-who', '<b>???</b>');
    updateBodyValByTag('t-howmuch', '?????');
    updateBodyValByTag('t-how', renderHowStepsHtml([text]));
    updateBodyValByTag('t-input', escapeHtml('???????'));
    updateBodyValByTag('t-output', '<b>???</b>' + escapeHtml('???????'));
    updateBodyValByTag('t-monitor', renderMonitorHtml(['???????']));

    if(document.querySelector('.sug-focus')){
      document.querySelector('.sug-focus').innerHTML = renderDiagnosisListItem('#e53935', 'i', 'ITBP????', text);
    }
    if(document.querySelector('.sug-act')){
      document.querySelector('.sug-act').innerHTML = renderDiagnosisListItem('#1a73e8', 'i', '????????', text);
    }
    Array.prototype.slice.call(document.querySelectorAll('.linear-roadmap .lr-ms-title')).forEach(function(node){
      node.textContent = '???';
    });
    Array.prototype.slice.call(document.querySelectorAll('.flow .flow-n')).forEach(function(node){
      var label = node.querySelector('.flow-lb');
      if(label){
        node.innerHTML = '<span class="flow-lb">' + label.textContent + '</span>' + escapeHtml('???');
      }
    });
  }

  function setText(selector, text){
    var el = document.querySelector(selector);
    if(el) el.textContent = text;
  }

  function escapeHtml(value){
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function uniqueTextList(values){
    return (values || []).filter(function(value, index, list){
      return value && list.indexOf(value) === index;
    });
  }

  function updateBodyValByTag(tagClass, html){
    var tag = document.querySelector('.body-tag.' + tagClass);
    var item = tag ? tag.closest('.body-item') : null;
    var val = item ? item.querySelector('.body-val') : null;
    if(val) val.innerHTML = html;
  }

  function getRequirementTypeBox(){
    return document.getElementById('requirementTypeBox');
  }

  function setRequirementTypeBox(typeName){
    var typeBox = getRequirementTypeBox();
    if(!typeBox) return;
    typeBox.textContent = 'AI ?????' + (typeName || '??????');
  }

  function findCodeByName(options, name, fallbackCode){
    var found = (options || []).find(function(option){
      return option.name === name;
    });

    if(found) return found.code;

    found = (options || []).find(function(option){
      return option.code === fallbackCode;
    });

    return found ? found.code : fallbackCode;
  }

  function mapBusinessDomainToUiCode(name){
    var normalized = String(name || '').trim();
    var aliases = {
      IPD: 'general',
      IPMS: 'sales',
      MTC: 'sales',
      SD: 'sales',
      Supply: 'procurement',
      Manufacturing: 'production',
      Procurement: 'procurement',
      Quality: 'general',
      MBTIT: 'general',
      General: 'general',
      ??: 'procurement',
      ??: 'finance',
      HR: 'hr',
      ??: 'legal',
      ??: 'warehouse',
      ??: 'production',
      ??: 'sales',
      ??: 'general',
      ?????: 'general'
    };

    return aliases[normalized] || findCodeByName(app.getDomainOptions(), normalized, 'general');
  }

  function formatListText(items, emptyText){
    return items && items.length ? items.join('?') : (emptyText || '???');
  }

  function formatPendingText(items){
    return items && items.length ? items.join('?') : '??';
  }

  function parsePendingQuestions(value){
    if(Array.isArray(value)){
      return normalizeArray(value);
    }
    return uniqueTextList(String(value || '')
      .split(/[\uFF1B;\n]+/)
      .map(function(item){ return item.trim(); })
      .filter(function(item){ return item && item !== '\u6682\u65E0'; }));
  }

  function normalizeOptionalAnswers(raw){
    var list = Array.isArray(raw) ? raw : [];
    return list.map(function(item){
      return {
        question: String((item && item.question) || '').trim(),
        answer: String((item && item.answer) || '').trim()
      };
    }).filter(function(item){
      return item.question || item.answer;
    });
  }

  function buildOptionalAnswersFromQuestions(questions, previousAnswers){
    var previous = normalizeOptionalAnswers(previousAnswers);
    var previousByQuestion = {};
    previous.forEach(function(item){
      if(item.question){
        previousByQuestion[item.question] = item.answer || '';
      }
    });
    return parsePendingQuestions(questions).map(function(question){
      return {
        question: question,
        answer: previousByQuestion[question] || ''
      };
    });
  }

  function renderOptionalAnswerFields(card){
    var answers = normalizeOptionalAnswers(card.optional_answers);
    if(!answers.length){
      answers = buildOptionalAnswersFromQuestions(card.pending_questions, []);
    }
    if(!answers.length){
      return '<div class="mvp-field-hint">\u5F53\u524D\u6CA1\u6709\u9700\u8981\u8865\u5145\u7684\u95EE\u9898\u3002\u8BE5\u533A\u57DF\u4E0D\u662F\u5FC5\u586B\u9879\u3002</div>';
    }
    return '<div class="mvp-field-hint">\u8FD9\u4E9B\u95EE\u9898\u4E0D\u662F\u5FC5\u586B\u3002\u82E5\u4F60\u77E5\u9053\u7B54\u6848\uFF0C\u53EF\u5728\u4E0B\u65B9\u8865\u5145\uFF1B\u4E0D\u77E5\u9053\u53EF\u4EE5\u7559\u7A7A\uFF0C\u95EE\u9898\u4F1A\u7EE7\u7EED\u4F5C\u4E3A\u5F85\u786E\u8BA4\u9879\u4FDD\u7559\u3002</div>' +
      '<div class="mvp-optional-answers">' +
      answers.map(function(item, index){
        return '<div class="mvp-optional-answer">' +
          '<div class="mvp-optional-question">' + (index + 1) + '. ' + escapeHtml(item.question || '\u5F85\u786E\u8BA4\u95EE\u9898') + '</div>' +
          '<textarea data-optional-answer-index="' + index + '" data-question="' + escapeHtml(item.question || '') + '" placeholder="\u53EF\u9009\u586B\u5199\uFF1A\u5982\u679C\u5DF2\u786E\u8BA4\uFF0C\u8BF7\u5199\u7B54\u6848\uFF1B\u4E0D\u77E5\u9053\u53EF\u7559\u7A7A\u3002">' + escapeHtml(item.answer || '') + '</textarea>' +
        '</div>';
      }).join('') +
      '</div>';
  }

  function normalizeStructuredReport(raw, fallback){
    var source = raw || {};
    var base = fallback || {};

    return {
      why: String(source.why || base.why || '?????').trim() || '?????',
      what: String(source.what || base.what || '?????').trim() || '?????',
      where: String(source.where || base.where || '?????').trim() || '?????',
      who: String(source.who || base.who || '?????').trim() || '?????',
      input: String(source.input || base.input || '?????').trim() || '?????',
      output: String(source.output || base.output || '?????').trim() || '?????',
      how: normalizeArray(source.how).length ? normalizeArray(source.how) : (normalizeArray(base.how).length ? normalizeArray(base.how) : ['?????']),
      monitor: normalizeArray(source.monitor).length ? normalizeArray(source.monitor) : (normalizeArray(base.monitor).length ? normalizeArray(base.monitor) : ['?????']),
      howmuch: String(source.howmuch || base.howmuch || '?????').trim() || '?????'
    };
  }

  function shortText(value, limit){
    var text = String(value || '').trim();
    if(!text) return '???';
    if(text.length <= limit){
      return text;
    }
    return text.slice(0, limit) + '...';
  }

  function buildThreeDimSummaryFromInsight(insight){
    return '????' + insight.domain.name + '??????' + formatListText((insight.pains || []).map(function(item){ return item.name; }), '???') + '??????' + formatListText((insight.actions || []).map(function(item){ return item.name; }), '???');
  }

  function buildAnalysisText(analysis){
    return 'AI ???????' + analysis.businessDomain + '??????????' + formatListText(analysis.painPoints, '???') + '?????????' + formatListText(analysis.systemActions, '???') + '??';
  }

  function normalizeArray(values){
    return uniqueTextList((Array.isArray(values) ? values : []).map(function(value){
      return String(value || '').trim();
    }).filter(Boolean));
  }

  function buildSelectionSummary(selectedOptions){
    var selected = selectedOptions || {};
    var parts = [];
    var roles = normalizeArray(selected.affected_roles);
    var focusPoints = normalizeArray(selected.focus_points);
    var expectations = normalizeArray(selected.system_expectations);

    if(roles.length){
      parts.push('?????' + roles.join('?'));
    }
    if(focusPoints.length){
      parts.push('?????' + focusPoints.join('?'));
    }
    if(expectations.length){
      parts.push('?????' + expectations.join('?'));
    }

    return parts.length ? parts.join('?') : '???????? AI ???????';
  }

  function buildInsightFromApiResult(result){
    var selection = {
      domainCode: mapBusinessDomainToUiCode(result.business_domain),
      painCodes: normalizeArray(result.pain_points).map(function(name){
        return findCodeByName(app.getPainOptions(), name);
      }).filter(Boolean),
      actionCodes: normalizeArray(result.system_actions).map(function(name){
        return findCodeByName(app.getActionOptions(), name);
      }).filter(Boolean)
    };

    return app.buildThreeDimensionalInsightFromSelection(selection);
  }

  function sanitizeQuickOptionLabel(value, group){
    var label = optionLabelByKeywords(value, group)
      .replace(/^??/, '')
      .replace(/??.*/, '')
      .replace(/??.*/, '')
      .replace(/[???!??;]/g, '')
      .trim();

    if(label.indexOf('?') > -1 || label.indexOf(',') > -1 || label.indexOf('?') > -1){
      return '';
    }
    if(label.length < 2 && !/^(IT|AI)$/.test(label)){
      return '';
    }
    if(label.length > 8){
      return '';
    }
    return label;
  }

  function normalizeQuickOptionGroup(rawValues, defaultValues, group){
    var roleLike = /???|??|??|??|??|??|??|??|???|???|ITBP|???/;
    var result = [];
    var seen = {};

    function addLabel(label){
      if(!label || seen[label]) return;
      seen[label] = true;
      result.push(label);
    }

    normalizeArray(rawValues).forEach(function(value){
      var parts = group === 'affected_roles'
        ? String(value).split(/[?,?/]/).map(function(item){ return item.trim(); }).filter(Boolean)
        : [value];

      parts.forEach(function(part){
        var label = sanitizeQuickOptionLabel(part, group);
        if(!label) return;
        if(group !== 'affected_roles' && roleLike.test(label)) return;
        addLabel(label);
      });
    });

    normalizeArray(defaultValues).forEach(function(value){
      var label = sanitizeQuickOptionLabel(value, group) || optionLabelByKeywords(value, group);
      if(group !== 'affected_roles' && roleLike.test(label)) return;
      addLabel(label);
    });

    return result.slice(0, 5);
  }

  function normalizeConfirmationOptions(rawOptions, domainCode){
    var defaults = app.getQuickSelectionOptionsByDomainCode(domainCode || 'general');
    var source = rawOptions || {};

    return {
      affected_roles: normalizeQuickOptionGroup(source.affected_roles, defaults.affected_roles, 'affected_roles'),
      focus_points: normalizeQuickOptionGroup(source.focus_points, defaults.focus_points, 'focus_points'),
      system_expectations: normalizeQuickOptionGroup(source.system_expectations, defaults.system_expectations, 'system_expectations')
    };
  }

  function compactText(value){
    return String(value || '')
      .replace(/[???!??;]/g, '')
      .replace(/^(??|??|?|????|??|??|??|??|??|??)/, '')
      .replace(/^(????|????|????)/, '')
      .replace(/(??|??|?|???|??|??|??|??|??)$/g, '')
      .trim();
  }

  function optionLabelByKeywords(value, group){
    var text = compactText(value);
    var rules = {
      affected_roles: [
        ['????,???,????,??', '??'],
        ['??????,???,??', '???'],
        ['????,????,??', '??'],
        ['????,??,??', '??'],
        ['???,???', '???'],
        ['????,??', '??'],
        ['?????,??', '??'],
        ['????,??,??,??', '??'],
        ['???', '???'],
        ['ITBP,IT', 'ITBP']
      ],
      focus_points: [
        ['???,???,???,???,???', '???'],
        ['??,????', '??'],
        ['???,???,????,??', '???'],
        ['????,??', '????'],
        ['??,??,?,?,?', '???'],
        ['??,??,???', '???'],
        ['??,??,??,??,??', '????'],
        ['??,??,??,???', '????'],
        ['??,??,?????', '????'],
        ['???,??', '????']
      ],
      system_expectations: [
        ['??,????,??', '????'],
        ['??,??,??,??', '????'],
        ['??,??,??,??', '????'],
        ['??,??,??,??', '????'],
        ['??,??,??,????', '????'],
        ['??,??', '????'],
        ['??,??,??,??', '????'],
        ['??,??,??', '????']
      ]
    };

    (rules[group] || []).some(function(rule){
      var keywords = rule[0].split(',');
      var label = rule[1];
      var matched = keywords.some(function(keyword){
        return keyword && text.indexOf(keyword) > -1;
      });
      if(matched){
        text = label;
      }
      return matched;
    });

    return text;
  }

  function buildQuickOptionMeta(option, group, usedLabels){
    var rawValue = String(option || '').trim();
    var label = optionLabelByKeywords(rawValue, group);

    label = label
      .replace(/^??/, '')
      .replace(/[?,].*$/, '')
      .replace(/??.*/, '')
      .replace(/??.*/, '')
      .trim();

    if(label.length > 8){
      label = label.slice(0, 8);
    }
    if(!label){
      label = rawValue.slice(0, 8) || '???';
    }
    if(usedLabels[label]){
      label = rawValue.slice(0, 8) || label;
    }
    usedLabels[label] = true;

    return {
      value: rawValue,
      label: label,
      description: rawValue
    };
  }

  function normalizeApiAnalysisResult(raw, input){
    var fallback = app.createFallbackApiAnalysis(input);
    var merged = Object.assign({}, fallback, raw || {});
    var type = app.detectRequirementType(input);
    var insight = buildInsightFromApiResult(merged);
    var painPoints = normalizeArray(merged.pain_points).length ? normalizeArray(merged.pain_points) : fallback.pain_points;
    var systemActions = normalizeArray(merged.system_actions).length ? normalizeArray(merged.system_actions) : fallback.system_actions;
    var targetUsers = normalizeArray(merged.target_users).length ? normalizeArray(merged.target_users) : normalizeArray(fallback.target_users);
    var uncertainItems = normalizeArray(merged.uncertain_items).length ? normalizeArray(merged.uncertain_items) : fallback.uncertain_items;
    var rewrittenRequest = String(merged.rewritten_request || fallback.rewritten_request || merged.suggested_request || fallback.suggested_request || '').trim();
    var diagnosis = Object.assign({}, fallback.diagnosis || {}, merged.diagnosis || {});
    var debug = merged.debug || {};
    var minimumSystemBehavior = normalizeArray(merged.minimum_system_behavior).length
      ? normalizeArray(merged.minimum_system_behavior)
      : (normalizeArray(diagnosis.minimum_system_behavior).length ? normalizeArray(diagnosis.minimum_system_behavior) : normalizeArray(diagnosis.desired_system_behavior));
    var currentManualProcess = String(merged.current_manual_process || diagnosis.current_manual_process || diagnosis.current_process || '').trim();
    var processBreakpoint = String(merged.process_breakpoint || diagnosis.process_breakpoint || '').trim();
    var passiveConsequence = String(merged.passive_consequence || diagnosis.passive_consequence || diagnosis.business_impact || '').trim();
    var businessObject = String(merged.business_object || diagnosis.business_object || '').trim();

    diagnosis.business_object = diagnosis.business_object || businessObject;
    diagnosis.current_manual_process = diagnosis.current_manual_process || currentManualProcess;
    diagnosis.current_process = diagnosis.current_process || currentManualProcess;
    diagnosis.process_breakpoint = diagnosis.process_breakpoint || processBreakpoint;
    diagnosis.passive_consequence = diagnosis.passive_consequence || passiveConsequence;
    diagnosis.business_impact = diagnosis.business_impact || passiveConsequence;
    diagnosis.minimum_system_behavior = normalizeArray(diagnosis.minimum_system_behavior).length ? normalizeArray(diagnosis.minimum_system_behavior) : minimumSystemBehavior;
    diagnosis.desired_system_behavior = normalizeArray(diagnosis.desired_system_behavior).length ? normalizeArray(diagnosis.desired_system_behavior) : minimumSystemBehavior;

    return {
      type: type,
      typeName: app.getRequirementTypeName(type),
      originalRequest: String(merged.original_request || input).trim(),
      rewrittenRequest: rewrittenRequest,
      businessDomain: merged.business_domain || fallback.business_domain,
      businessObject: businessObject,
      painPoints: painPoints,
      systemActions: systemActions,
      targetUsers: targetUsers,
      diagnosis: diagnosis,
      currentManualProcess: currentManualProcess,
      processBreakpoint: processBreakpoint,
      passiveConsequence: passiveConsequence,
      minimumSystemBehavior: minimumSystemBehavior,
      relatedSystems: normalizeArray(merged.related_systems).length ? normalizeArray(merged.related_systems) : normalizeArray(fallback.related_systems),
      candidateSystems: normalizeArray(merged.candidate_systems).length ? normalizeArray(merged.candidate_systems) : normalizeArray(fallback.candidate_systems),
      warnings: normalizeArray(merged.warnings),
      realIntent: String(merged.real_intent || fallback.real_intent || '').trim(),
      suggestedRequest: String(merged.suggested_request || fallback.suggested_request || '').trim(),
      uncertainItems: uncertainItems,
      confirmationOptions: normalizeConfirmationOptions(merged.confirmation_options, insight.domainCode),
      scenarioForm: merged.scenario_form || fallback.scenario_form || null,
      structuredReport: normalizeStructuredReport(merged.structured_report, fallback.structured_report),
      threeDimInsight: insight,
      aiUnderstanding: buildAnalysisText({
        businessDomain: merged.business_domain || fallback.business_domain,
        painPoints: painPoints,
        systemActions: systemActions
      }),
      mode: merged.mode || fallback.mode || 'mock',
      debug: debug,
      qualityPassed: debug.quality_passed !== false,
      qualityIssues: normalizeArray(debug.quality_issues)
    };
  }

  function clearThreeDimModule(){
    var summary = document.getElementById('threeDimSummaryText');
    var domainSelect = document.getElementById('threeDimDomainSelect');
    var painBox = document.getElementById('painOptionList');
    var actionBox = document.getElementById('actionOptionList');
    var guess = document.getElementById('realIntentGuessText');
    var uncertain = document.getElementById('uncertainItemList');

    if(summary) summary.textContent = '';
    if(domainSelect) domainSelect.innerHTML = '';
    if(painBox) painBox.innerHTML = '';
    if(actionBox) actionBox.innerHTML = '';
    if(guess) guess.textContent = '';
    if(uncertain) uncertain.innerHTML = '';
  }

  function clearQuickSelectionModule(){
    ['affectedRolesOptions', 'focusPointOptions', 'systemExpectationOptions'].forEach(function(id){
      var container = document.getElementById(id);
      if(container) container.innerHTML = '';
    });
  }

  function fillDemoExample(){
    var input = document.getElementById('userRequestInput');
    if(!input) return;
    input.value = '????????????????BOM???????SAP????????????';
    showMvpStatus('?????????AI ????????');
  }

  function restoreInitialReport(){
    setText('.orig-text', initialReportState.origText);
    setText('.newreq-sentence', initialReportState.newSentence);
    setText('.detail-body', initialReportState.detailBody);

    if(document.querySelector('.sug-focus')){
      document.querySelector('.sug-focus').innerHTML = initialReportState.sugFocusHtml;
    }
    if(document.querySelector('.sug-act')){
      document.querySelector('.sug-act').innerHTML = initialReportState.sugActHtml;
    }
    if(document.querySelector('.linear-roadmap')){
      document.querySelector('.linear-roadmap').innerHTML = initialReportState.roadmapHtml;
    }
    if(document.querySelector('.flow')){
      document.querySelector('.flow').innerHTML = initialReportState.flowHtml;
    }

    updateBodyValByTag('t-why', initialReportState.whyHtml);
    updateBodyValByTag('t-what', initialReportState.whatHtml);
    updateBodyValByTag('t-wheren', initialReportState.whereHtml);
    updateBodyValByTag('t-who', initialReportState.whoHtml);
    updateBodyValByTag('t-how', initialReportState.howHtml);
    updateBodyValByTag('t-howmuch', initialReportState.howmuchHtml);
    updateBodyValByTag('t-input', initialReportState.inputHtml);
    updateBodyValByTag('t-output', initialReportState.outputHtml);
    updateBodyValByTag('t-monitor', initialReportState.monitorHtml);
  }

  function resetMvpDemo(){
    var input = document.getElementById('userRequestInput');
    var clarifyPanel = document.getElementById('mvp-clarify-panel');
    var cardPanel = document.getElementById('mvp-card-panel');
    var output = document.getElementById('submitOutput');
    var typeBox = getRequirementTypeBox();
    var aiText = document.getElementById('aiUnderstandingText');
    var demandCard = document.getElementById('demandCard');

    if(input) input.value = '';
    if(clarifyPanel) clarifyPanel.style.display = 'none';
    if(cardPanel) cardPanel.style.display = 'none';
    if(output) output.classList.remove('show');
    if(typeBox) typeBox.textContent = '';
    if(aiText) aiText.textContent = '';
    if(demandCard) demandCard.innerHTML = '';
    renderScenarioForm(null);

    clearThreeDimModule();
    clearQuickSelectionModule();
    restoreInitialReport();

    mvpState.original = '';
    mvpState.analysis = null;
    mvpState.card = null;
    mvpState.selectedOptions = {
      affected_roles: [],
      focus_points: [],
      system_expectations: [],
      scenario_answers: {}
    };
    mvpState.fastAnalysisStatus = 'idle';
    mvpState.deepAnalysisStatus = 'idle';
    mvpState.deepAnalysis = null;
    setDeepAnalysisStatus('idle', '?????????????????????ITBP???????????');

    showMvpStatus('????????');
  }

  function renderCheckboxGroup(containerId, options, selectedCodes, inputName){
    var container = document.getElementById(containerId);

    if(!container) return;

    container.innerHTML = '';

    (options || []).forEach(function(option){
      var label = document.createElement('label');
      var input = document.createElement('input');
      var text = document.createElement('span');

      label.className = 'mvp-check';
      input.type = 'checkbox';
      input.name = inputName;
      input.value = option.code;
      input.checked = selectedCodes.indexOf(option.code) > -1;
      input.addEventListener('change', handleThreeDimInsightChange);

      text.textContent = option.name;
      label.appendChild(input);
      label.appendChild(text);
      container.appendChild(label);
    });
  }

  function renderTagList(containerId, items, emptyText){
    var container = document.getElementById(containerId);

    if(!container) return;

    container.innerHTML = '';

    if(!items || !items.length){
      container.innerHTML = '<span class="mvp-tag muted">' + escapeHtml(emptyText || '??') + '</span>';
      return;
    }

    items.forEach(function(item){
      var tag = document.createElement('span');
      tag.className = 'mvp-tag';
      tag.textContent = item;
      container.appendChild(tag);
    });
  }

  function renderChipGroup(containerId, options, selectedValues, inputName, groupKey){
    var container = document.getElementById(containerId);
    var usedLabels = {};

    if(!container) return;

    container.innerHTML = '';

    (options || []).forEach(function(option){
      var meta = buildQuickOptionMeta(option, groupKey || inputName, usedLabels);
      var label = document.createElement('label');
      var input = document.createElement('input');
      var text = document.createElement('span');

      label.className = 'mvp-chip';
      label.title = meta.description;
      input.type = 'checkbox';
      input.name = inputName;
      input.value = meta.value;
      input.checked = selectedValues.indexOf(meta.value) > -1;
      input.addEventListener('change', handleQuickSelectionChange);

      text.textContent = meta.label;
      label.appendChild(input);
      label.appendChild(text);
      container.appendChild(label);
    });
  }

  function renderQuickSelections(options, selectedOptions){
    renderChipGroup('affectedRolesOptions', options.affected_roles, selectedOptions.affected_roles, 'affected_roles', 'affected_roles');
    renderChipGroup('focusPointOptions', options.focus_points, selectedOptions.focus_points, 'focus_points', 'focus_points');
    renderChipGroup('systemExpectationOptions', options.system_expectations, selectedOptions.system_expectations, 'system_expectations', 'system_expectations');
  }

  function renderScenarioForm(form){
    var card = document.getElementById('scenarioFormCard');
    var box = document.getElementById('scenarioFormBox');
    var hint = document.getElementById('scenarioFormHint');

    if(!card || !box) return;

    if(!form || !Array.isArray(form.groups) || !form.groups.length){
      card.style.display = 'none';
      box.innerHTML = '';
      return;
    }

    card.style.display = '';
    if(hint){
      hint.textContent = (form.template_name || '??????') + (form.match_reason ? '?' + form.match_reason : '');
    }
    box.innerHTML = form.groups.map(function(group){
      var options = Array.isArray(group.options) ? group.options : [];
      return '<div class="mvp-choice-card">' +
        '<div class="mvp-choice-title">' + escapeHtml(group.title || '?????') + (group.required ? ' <span class="mvp-source pending">???</span>' : '') + '</div>' +
        '<div class="mvp-chip-group">' +
          options.map(function(option){
            return '<label class="mvp-chip" title="' + escapeHtml(option) + '">' +
              '<input type="checkbox" name="scenario_' + escapeHtml(group.key || 'question') + '" value="' + escapeHtml(option) + '">' +
              '<span>' + escapeHtml(option) + '</span>' +
            '</label>';
          }).join('') +
        '</div>' +
      '</div>';
    }).join('');
  }

  function collectScenarioAnswers(){
    var result = {};
    document.querySelectorAll('#scenarioFormBox input[type="checkbox"]:checked').forEach(function(input){
      var key = String(input.name || '').replace(/^scenario_/, '') || 'question';
      if(!result[key]) result[key] = [];
      result[key].push(input.value);
    });
    return result;
  }

  function getCheckedValues(selector){
    return Array.prototype.slice.call(document.querySelectorAll(selector)).filter(function(input){
      return input.checked;
    }).map(function(input){
      return input.value;
    });
  }

  function collectSelectedOptions(){
    // ???????
    var clarifitems = {};
    document.querySelectorAll('.clarify-reminder.checked').forEach(function(el){
      var dimension = el.getAttribute('data-dimension');
      var value = el.getAttribute('data-value');
      if(dimension && value){
        if(!clarifitems[dimension]){
          clarifitems[dimension] = [];
        }
        clarifitems[dimension].push(value);
      }
    });

    return {
      affected_roles: getCheckedValues('#affectedRolesOptions input[type="checkbox"]'),
      focus_points: getCheckedValues('#focusPointOptions input[type="checkbox"]'),
      system_expectations: getCheckedValues('#systemExpectationOptions input[type="checkbox"]'),
      clarify_items: clarifitems,
      scenario_answers: collectScenarioAnswers()
    };
  }

  function renderThreeDimInsight(insight){
    var domainSelect = document.getElementById('threeDimDomainSelect');
    var summary = document.getElementById('threeDimSummaryText');
    var guess = document.getElementById('realIntentGuessText');
    var domainOptions = app.getDomainOptions();

    if(domainSelect){
      domainSelect.innerHTML = '';
      domainOptions.forEach(function(option){
        var el = document.createElement('option');
        el.value = option.code;
        el.textContent = option.name;
        el.selected = option.code === insight.domainCode;
        domainSelect.appendChild(el);
      });
      domainSelect.onchange = handleThreeDimInsightChange;
    }

    renderCheckboxGroup('painOptionList', app.getPainOptions(), insight.painCodes || [], 'painOptions');
    renderCheckboxGroup('actionOptionList', app.getActionOptions(), insight.actionCodes || [], 'actionOptions');

    if(summary){
      summary.textContent = buildThreeDimSummaryFromInsight(insight);
    }

    if(guess && mvpState.analysis){
      guess.textContent = mvpState.analysis.realIntent || '';
    }

    renderTagList('uncertainItemList', mvpState.analysis ? mvpState.analysis.uncertainItems : [], '???');
  }

  function buildSuccessMetric(analysis){
    var report = mvpState.deepAnalysisStatus === 'success' ? (analysis.structuredReport || {}) : {};
    var monitor = normalizeArray(report.monitor);
    if(monitor.length){
      return monitor.join('?');
    }

    var domainName = analysis.businessDomain === '??' ? '????' : analysis.businessDomain;
    return domainName + '??????????????????';
  }

  function buildCardFromState(){
    var analysis = mvpState.analysis;
    var selected = mvpState.selectedOptions;
    var deepReady = mvpState.deepAnalysisStatus === 'success';
    var report = deepReady ? (analysis.structuredReport || normalizeStructuredReport()) : normalizeStructuredReport({
      why: formatListText(analysis.painPoints, '?????'),
      what: analysis.suggestedRequest || analysis.rewrittenRequest || '?????',
      who: formatListText(analysis.targetUsers, '?????'),
      input: '?????',
      output: formatListText(analysis.systemActions, '?????'),
      how: ['?????ITBP????'],
      monitor: ['?????ITBP????']
    });
    var targetUsers = normalizeArray(selected.affected_roles).length ? normalizeArray(selected.affected_roles) : normalizeArray(analysis.targetUsers);
    var focusPoints = normalizeArray(selected.focus_points);
    var expectations = normalizeArray(selected.system_expectations);
    var diagnosis = deepReady ? Object.assign({}, analysis.diagnosis || {}) : {};

    diagnosis.business_object = diagnosis.business_object || (deepReady ? analysis.businessObject : '') || '?????ITBP????';
    diagnosis.current_manual_process = diagnosis.current_manual_process || (deepReady ? analysis.currentManualProcess : '') || diagnosis.current_process || '?????ITBP????';
    diagnosis.current_process = diagnosis.current_process || diagnosis.current_manual_process;
    diagnosis.process_breakpoint = diagnosis.process_breakpoint || (deepReady ? analysis.processBreakpoint : '') || '?????ITBP????';
    diagnosis.passive_consequence = diagnosis.passive_consequence || (deepReady ? analysis.passiveConsequence : '') || diagnosis.business_impact || '?????ITBP????';
    diagnosis.business_impact = diagnosis.business_impact || diagnosis.passive_consequence;
    diagnosis.minimum_system_behavior = normalizeArray(diagnosis.minimum_system_behavior).length ? normalizeArray(diagnosis.minimum_system_behavior) : (deepReady ? normalizeArray(analysis.minimumSystemBehavior) : ['?????ITBP????']);
    diagnosis.desired_system_behavior = normalizeArray(diagnosis.desired_system_behavior).length ? normalizeArray(diagnosis.desired_system_behavior) : diagnosis.minimum_system_behavior;

    return {
      requirement_type: analysis.typeName,
      requirement_type_code: analysis.type,
      original_request: analysis.originalRequest || mvpState.original,
      rewritten_request: analysis.rewrittenRequest || analysis.suggestedRequest,
      ai_understanding: analysis.aiUnderstanding,
      core_goal: analysis.realIntent,
      real_intent_guess: analysis.realIntent,
      refined_request: analysis.suggestedRequest,
      pending_questions: formatPendingText(analysis.uncertainItems),
      optional_answers: buildOptionalAnswersFromQuestions(analysis.uncertainItems, analysis.optionalAnswers),
      pain_point: report.why || formatListText(analysis.painPoints, '?????'),
      target_user: formatListText(targetUsers, report.who || '?????'),
      system_action: formatListText(analysis.systemActions, '???'),
      input_data: report.input || formatListText(focusPoints, '?????'),
      output_result: report.output || formatListText(expectations, '?????'),
      delivery_method: expectations.length ? expectations.join('?') : '?????',
      success_metric: buildSuccessMetric(analysis),
      domain_name: analysis.businessDomain,
      pain_labels: formatListText(analysis.painPoints, '???'),
      action_labels: formatListText(analysis.systemActions, '???'),
      three_dim_summary: buildThreeDimSummaryFromInsight(analysis.threeDimInsight),
      target_users_list: targetUsers,
      selected_constraints: buildSelectionSummary(selected),
      diagnosis: diagnosis,
      related_systems: analysis.relatedSystems || [],
      candidate_systems: analysis.candidateSystems || [],
      warnings: analysis.warnings || [],
      structured_report: report,
      quality_passed: analysis.qualityPassed !== false,
      quality_issues: normalizeArray(analysis.qualityIssues),
      debug: analysis.debug || {}
    };
  }

  function renderDemandCard(card){
    var box = document.getElementById('demandCard');
    var qualityNote = card.quality_passed === false
      ? '<div class="mvp-quality-note">AI \u521D\u7A3F\u4ECD\u9700 ITBP \u786E\u8BA4</div>'
      : '';

    if(!box) return;

    box.innerHTML =
      qualityNote +
      '<div class="mvp-field full">' +
        '<label><span>\u53EF\u63D0\u4EA4\u7248\u672C</span><span class="mvp-source ai">AI \u5EFA\u8BAE\u7A3F</span></label>' +
        '<div class="mvp-field-hint">\u8FD9\u662F\u53EF\u76F4\u63A5\u63D0\u4EA4\u6216\u7EE7\u7EED\u4FEE\u6539\u7684\u9700\u6C42\u63CF\u8FF0\u3002</div>' +
        '<textarea data-field="refined_request">' + escapeHtml(card.refined_request || card.rewritten_request || '') + '</textarea>' +
      '</div>' +
      '<div class="mvp-field full">' +
        '<label><span>\u5F85\u786E\u8BA4\u95EE\u9898</span><span class="mvp-source pending">\u9009\u586B\uFF0C\u4E0D\u5F71\u54CD\u63D0\u4EA4</span></label>' +
        '<div class="mvp-field-hint">\u8FD9\u4E9B\u662F AI \u8BC6\u522B\u51FA\u7684\u5173\u952E\u6F84\u6E05\u70B9\u3002\u4E0D\u77E5\u9053\u7B54\u6848\u53EF\u4EE5\u4FDD\u7559\uFF0C\u540E\u7EED\u7531\u4E1A\u52A1\u6216 ITBP \u7EE7\u7EED\u786E\u8BA4\u3002</div>' +
        '<textarea data-field="pending_questions">' + escapeHtml(card.pending_questions || '') + '</textarea>' +
      '</div>' +
      '<div class="mvp-field full">' +
        '<label><span>\u53EF\u9009\u56DE\u7B54 / \u8865\u5145\u8BF4\u660E</span><span class="mvp-source user">\u9009\u586B</span></label>' +
        renderOptionalAnswerFields(card) +
      '</div>';
  }

  function getEditedCard(){
    var card = Object.assign({}, mvpState.card || {});

    document.querySelectorAll('#demandCard textarea[data-field]').forEach(function(textarea){
      card[textarea.getAttribute('data-field')] = textarea.value.trim();
    });

    card.optional_answers = [];
    document.querySelectorAll('#demandCard textarea[data-optional-answer-index]').forEach(function(textarea){
      card.optional_answers.push({
        question: textarea.getAttribute('data-question') || '',
        answer: textarea.value.trim()
      });
    });
    card.answered_clarifications = normalizeOptionalAnswers(card.optional_answers).filter(function(item){
      return item.answer;
    });

    if(card.refined_request){
      card.rewritten_request = card.refined_request;
    }

    return applyOptionalAnswersToCard(card);
  }

  function optionalAnswerSummary(card){
    var answered = normalizeOptionalAnswers(card.answered_clarifications || card.optional_answers).filter(function(item){
      return item.answer;
    });
    if(!answered.length) return '';
    return answered.map(function(item){
      return item.answer;
    }).join('\uFF1B');
  }

  function inferInventorySupplementFacts(summary){
    var text = String(summary || '');
    return {
      source: text.indexOf('WMS') > -1 || text.indexOf('wms') > -1
        ? (text.indexOf('ERP') > -1 || text.indexOf('erp') > -1 ? '\u0057\u004D\u0053\u5E93\u5B58\u4E3A\u4E3B\u3001\u0045\u0052\u0050\u5E93\u5B58\u4E3A\u8F85' : '\u0057\u004D\u0053\u5E93\u5B58')
        : '',
      quantity: text.indexOf('\u9884\u7559') > -1
        ? '\u53EF\u7528\u91CF\uFF0C\u5E76\u6263\u51CF\u5DF2\u9884\u7559\u6570\u91CF'
        : (text.indexOf('\u53EF\u7528\u91CF') > -1 ? '\u53EF\u7528\u91CF' : ''),
      stocktake: text.indexOf('\u76D8\u70B9') > -1
        ? '\u76D8\u70B9\u5DEE\u5F02\u8F83\u5927\u65F6\u63D0\u9192\u4ED3\u5E93\u4EBA\u5DE5\u786E\u8BA4'
        : ''
    };
  }

  function buildFusedRefinedRequest(card, summary){
    var base = String(card.refined_request || card.rewritten_request || '').trim();
    var facts = inferInventorySupplementFacts(summary);
    var source = facts.source || '\u5E93\u5B58\u6570\u636E';
    var quantity = facts.quantity || '\u53EF\u7528\u5E93\u5B58';
    var stocktake = facts.stocktake;

    if(!summary){
      return base;
    }

    if(base.indexOf('\u5E93\u5B58') > -1 || base.indexOf('\u4E0B\u5355') > -1){
      return '\u4E1A\u52A1\u4E0B\u5355\u524D\uFF0C\u7CFB\u7EDF\u4EE5' + source +
        '\u6821\u9A8C' + quantity +
        '\uFF0C\u81EA\u52A8\u5C55\u793A\u5E93\u5B58\u5DEE\u5F02\u5E76\u63D0\u9192\u76F8\u5173\u4EBA\u5458' +
        (stocktake ? '\uFF1B' + stocktake : '') +
        '\uFF0C\u907F\u514D\u7F3A\u8D27\u6216\u8D85\u5356\u540E\u624D\u88AB\u52A8\u5904\u7406\u3002';
    }

    return base;
  }

  function applyOptionalAnswersToCard(card){
    var summary = optionalAnswerSummary(card);
    var report = Object.assign({}, card.structured_report || {});

    if(!summary){
      card.structured_report = report;
      return card;
    }

    card.confirmed_supplement = summary;
    card.refined_request = buildFusedRefinedRequest(card, summary);
    card.rewritten_request = card.refined_request;

    var facts = inferInventorySupplementFacts(summary);
    if(facts.source || facts.quantity){
      report.input = '\u4EE5' + (facts.source || '\u5E93\u5B58\u6570\u636E') + '\uFF0C\u4E0B\u5355\u524D\u6821\u9A8C' + (facts.quantity || '\u53EF\u7528\u5E93\u5B58') + (facts.stocktake ? '\uFF1B' + facts.stocktake : '');
    }else if(report.input){
      report.input = report.input + '\uFF1B\u4E1A\u52A1\u8865\u5145\uFF1A' + summary;
    }else{
      report.input = '\u4E1A\u52A1\u8865\u5145\uFF1A' + summary;
    }

    if(facts.source || facts.quantity || facts.stocktake){
      report.output = '\u8F93\u51FA\u5E93\u5B58\u53EF\u7528\u91CF\u3001\u5DF2\u9884\u7559\u6570\u91CF\u3001\u5DEE\u5F02\u63D0\u9192\u548C\u4EBA\u5DE5\u786E\u8BA4\u4EFB\u52A1';
    }

    card.structured_report = report;
    return card;
  }

  function makeFrontDetailTextFromCard(card){
    return app.makeDetailText(card);
  }

  function renderHowStepsHtml(steps){
    var safeSteps = normalizeArray(steps).length ? normalizeArray(steps) : ['?????'];

    return '<div class="how-steps">' + safeSteps.map(function(step, index){
      return '<div class="how-step"><b>S' + (index + 1) + '</b><br>' + escapeHtml(step) + '</div>';
    }).join('') + '</div>';
  }

  function renderMonitorHtml(items){
    var safeItems = normalizeArray(items).length ? normalizeArray(items) : ['?????'];

    return '<div class="mon-steps">' + safeItems.map(function(item, index){
      var cls = index === safeItems.length - 1 ? 'mon-step mon-result' : 'mon-step';
      var label = index === safeItems.length - 1 ? '??' : ('??' + (index + 1));
      return '<div class="' + cls + '"><b>' + label + '</b><br>' + escapeHtml(item) + '</div>';
    }).join('') + '</div>';
  }

  function formatDiagnosisList(values, emptyText){
    return normalizeArray(values).length ? normalizeArray(values).join('?') : (emptyText || '?????');
  }

  function renderDiagnosisListItem(color, number, title, value){
    return '<li><span class="sug-nb" style="background:' + color + '">' + number + '</span><b>' + escapeHtml(title) + '?</b>' + escapeHtml(value || '?????') + '</li>';
  }

  function renderInlineTags(items, emptyText){
    var values = normalizeArray(items);
    if(!values.length){
      return '<span class="mvp-tag muted">' + escapeHtml(emptyText || '??') + '</span>';
    }
    return values.slice(0, 3).map(function(item){
      return '<span class="mvp-tag">' + escapeHtml(item) + '</span>';
    }).join('');
  }

  function updateRoadmap(card){
    var titles = document.querySelectorAll('.linear-roadmap .lr-ms-title');
    var report = card.structured_report || {};
    var how = normalizeArray(report.how);
    var monitor = normalizeArray(report.monitor);
    var values = [
      shortText(report.why, 16),
      shortText(report.what, 16),
      shortText(report.where, 16),
      shortText(how[0], 16),
      shortText(how[1], 16),
      shortText(report.output, 16),
      shortText(how[2], 16),
      shortText(monitor[0], 16)
    ];

    Array.prototype.slice.call(titles).forEach(function(node, index){
      if(values[index]){
        node.textContent = values[index];
      }
    });
  }

  function updateFlowChart(card){
    var report = card.structured_report || {};
    var nodes = document.querySelectorAll('.flow .flow-n');
    var how = normalizeArray(report.how);
    var monitor = normalizeArray(report.monitor);
    var values = [
      report.input,
      report.what,
      how.length ? how.join(' ? ') : '?????',
      report.why,
      report.where,
      report.who,
      report.output,
      monitor.length ? monitor.join(' ? ') : '?????'
    ];

    Array.prototype.slice.call(nodes).forEach(function(node, index){
      var label = node.querySelector('.flow-lb');
      if(!label || !values[index]) return;
      node.innerHTML = '<span class="flow-lb">' + label.textContent + '</span>' + escapeHtml(values[index]);
    });
  }

  function updateSuggestionArea(card){
    var focusList = document.querySelector('.sug-focus');
    var actList = document.querySelector('.sug-act');
    var report = card.structured_report || {};
    var diagnosis = card.diagnosis || {};

    if(focusList){
      focusList.innerHTML =
        renderDiagnosisListItem('#e53935', '1', '????', diagnosis.business_object || '?????') +
        renderDiagnosisListItem('#e53935', '2', '??????', diagnosis.current_manual_process || diagnosis.current_process || report.where) +
        renderDiagnosisListItem('#e53935', '3', '????', diagnosis.process_breakpoint) +
        renderDiagnosisListItem('#e53935', '4', '????', diagnosis.passive_consequence || diagnosis.business_impact);
    }

    if(actList){
      actList.innerHTML =
        renderDiagnosisListItem('#1a73e8', '1', '??????', formatDiagnosisList(diagnosis.minimum_system_behavior || diagnosis.desired_system_behavior, report.output)) +
        renderDiagnosisListItem('#1a73e8', '2', '????', diagnosis.pain_root_cause || report.why) +
        renderDiagnosisListItem('#1a73e8', '3', '????', card.pending_questions || formatDiagnosisList(diagnosis.uncertain_items)) +
        renderDiagnosisListItem('#1a73e8', '?', '??????', card.refined_request || '???');
    }
  }

  function syncAnalysisByInsight(resetCard){
    var analysis;
    var selection;
    var insight;
    var previousSelections;

    if(!mvpState.analysis) return;

    analysis = mvpState.analysis;
    previousSelections = mvpState.selectedOptions;
    selection = {
      domainCode: document.getElementById('threeDimDomainSelect').value,
      painCodes: getCheckedValues('#painOptionList input[type="checkbox"]'),
      actionCodes: getCheckedValues('#actionOptionList input[type="checkbox"]')
    };
    insight = app.buildThreeDimensionalInsightFromSelection(selection);

    analysis.threeDimInsight = insight;
    analysis.businessDomain = insight.domain.name;
    analysis.painPoints = (insight.pains || []).map(function(item){ return item.name; });
    analysis.systemActions = (insight.actions || []).map(function(item){ return item.name; });
    analysis.realIntent = app.buildRealIntentGuess(analysis.type, insight);
    analysis.aiUnderstanding = buildAnalysisText(analysis);
    analysis.confirmationOptions = app.getQuickSelectionOptionsByDomainCode(insight.domain.code);
    if(!normalizeArray(analysis.targetUsers).length){
      analysis.targetUsers = (analysis.confirmationOptions.affected_roles || []).slice(0, 2);
    }
    mvpState.selectedOptions = {
      affected_roles: normalizeArray(previousSelections.affected_roles).filter(function(item){
        return analysis.confirmationOptions.affected_roles.indexOf(item) > -1;
      }),
      focus_points: normalizeArray(previousSelections.focus_points).filter(function(item){
        return analysis.confirmationOptions.focus_points.indexOf(item) > -1;
      }),
      system_expectations: normalizeArray(previousSelections.system_expectations).filter(function(item){
        return analysis.confirmationOptions.system_expectations.indexOf(item) > -1;
      }),
      scenario_answers: collectScenarioAnswers()
    };

    if(!analysis.uncertainItems || !analysis.uncertainItems.length){
      analysis.uncertainItems = app.buildUncertainItemsForInsight(insight);
    }

    setText('#aiUnderstandingText', analysis.aiUnderstanding);
    renderThreeDimInsight(insight);
    renderQuickSelections(analysis.confirmationOptions, mvpState.selectedOptions);

    if(resetCard && mvpState.card){
      mvpState.card = buildCardFromState();
      renderDemandCard(mvpState.card);
      document.getElementById('submitOutput').classList.remove('show');
    }
  }

  function handleThreeDimInsightChange(){
    syncAnalysisByInsight(true);
    showMvpStatus('AI ????????????????????????????');
  }

  function handleQuickSelectionChange(){
    mvpState.selectedOptions = collectSelectedOptions();
  }

  async function postJson(path, payload){
    var response = await fetch(path, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });
    var data = await response.json().catch(function(){
      return {};
    });

    if(!response.ok){
      throw new Error(data.error || ('?????' + response.status));
    }

    return data;
  }


  function serializeFastAnalysisForApi(){
    var analysis = mvpState.analysis;

    return {
      original_request: analysis.originalRequest,
      rewritten_request: analysis.rewrittenRequest,
      business_domain: analysis.businessDomain,
      business_object: analysis.businessObject,
      pain_points: analysis.painPoints,
      system_actions: analysis.systemActions,
      target_users: analysis.targetUsers,
      related_systems: analysis.relatedSystems || [],
      candidate_systems: analysis.candidateSystems || [],
      real_intent: analysis.realIntent,
      suggested_request: analysis.suggestedRequest,
      confirmation_options: analysis.confirmationOptions,
      scenario_form: analysis.scenarioForm,
      uncertain_items: analysis.uncertainItems,
      warnings: analysis.warnings || [],
      debug: analysis.debug || {}
    };
  }
  function serializeAnalysisForApi(){
    var analysis = mvpState.analysis;

    return {
      original_request: analysis.originalRequest,
      rewritten_request: analysis.rewrittenRequest,
      business_domain: analysis.businessDomain,
      business_object: analysis.businessObject,
      pain_points: analysis.painPoints,
      system_actions: analysis.systemActions,
      target_users: analysis.targetUsers,
      current_manual_process: analysis.currentManualProcess,
      process_breakpoint: analysis.processBreakpoint,
      passive_consequence: analysis.passiveConsequence,
      minimum_system_behavior: analysis.minimumSystemBehavior,
      diagnosis: analysis.diagnosis || {},
      related_systems: analysis.relatedSystems || [],
      candidate_systems: analysis.candidateSystems || [],
      real_intent: analysis.realIntent,
      suggested_request: analysis.suggestedRequest,
      confirmation_options: analysis.confirmationOptions,
      scenario_form: analysis.scenarioForm,
      uncertain_items: analysis.uncertainItems,
      structured_report: analysis.structuredReport,
      warnings: analysis.warnings || [],
      debug: analysis.debug || {}
    };
  }

  async function startClarify(){
    var inputEl = document.getElementById('userRequestInput');
    var input = inputEl ? inputEl.value.trim() : '';
    var rawResult;
    var modeMessage;

    if(!input){
      alert('??????????');
      if(inputEl) inputEl.focus();
      return;
    }

    showMvpStatus('AI ??????????...');
    showAiThinking('AI ??????????????????????');
    setButtonLoading('startClarifyBtn', true, '???...');
    renderCardLoading('AI????????...');
    mvpState.original = input;
    mvpState.card = null;
    mvpState.fastAnalysisStatus = 'loading';
    mvpState.deepAnalysisStatus = 'idle';
    mvpState.deepAnalysis = null;
    mvpState.selectedOptions = {
      affected_roles: [],
      focus_points: [],
      system_expectations: [],
      scenario_answers: {}
    };
    setDeepAnalysisStatus('idle', '?????????????????????ITBP???????????');

    try{
      rawResult = await postJson('/api/analyze_fast', { user_input: input });
      mvpState.fastAnalysisStatus = 'success';
    }catch(error){
      rawResult = app.createFallbackApiAnalysis(input);
      rawResult.mode = 'local-fallback';
      rawResult.error_message = error.message;
      mvpState.fastAnalysisStatus = 'error';
    }

    mvpState.analysis = normalizeApiAnalysisResult(rawResult, input);
    mvpState.card = buildCardFromState();
    setDeepAnalysisStatus('idle', '?????????????????????ITBP???????????');

    setRequirementTypeBox(mvpState.analysis.typeName);
    setText('#aiUnderstandingText', mvpState.analysis.aiUnderstanding);
    renderThreeDimInsight(mvpState.analysis.threeDimInsight);
    renderQuickSelections(mvpState.analysis.confirmationOptions, mvpState.selectedOptions);
    renderScenarioForm(mvpState.analysis.scenarioForm);
    renderDemandCard(mvpState.card);
    updateFrontReportFromCard(mvpState.card);

    document.getElementById('mvp-clarify-panel').style.display = '';
    document.getElementById('mvp-card-panel').style.display = '';
    document.getElementById('submitOutput').classList.remove('show');

    modeMessage = mvpState.analysis.mode === 'llm'
      ? 'AI ????????????????????????'
      : '???? mock ?????????????????????????';

    showMvpStatus(modeMessage);
    setButtonLoading('startClarifyBtn', false);
    showAiSuccess('AI ????????????????????????');
    document.getElementById('mvp-clarify-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function fillQuestionExample(){
    var analysis = mvpState.analysis;

    if(!analysis){
      alert('?????AI ?????');
      return;
    }

    mvpState.selectedOptions = {
      affected_roles: (analysis.confirmationOptions.affected_roles || []).slice(0, 2),
      focus_points: (analysis.confirmationOptions.focus_points || []).slice(0, 2),
      system_expectations: (analysis.confirmationOptions.system_expectations || []).slice(0, 2),
      scenario_answers: collectScenarioAnswers()
    };

    renderQuickSelections(analysis.confirmationOptions, mvpState.selectedOptions);
    showMvpStatus('?????????');
  }

  async function generateDemandCard(){
    var rawResult;

    if(!mvpState.analysis){
      alert('?????AI ?????');
      return;
    }

    mvpState.selectedOptions = collectSelectedOptions();
    mvpState.selectedOptions.scenario_answers = collectScenarioAnswers();
    showMvpStatus('AI ??????????????...');
    showAiThinking('AI ???????????????????');
    setButtonLoading('generateDemandBtn', true, '???...');

    try{
      rawResult = await postJson('/api/refine', {
        user_input: mvpState.original,
        analysis_result: serializeFastAnalysisForApi(),
        selected_options: Object.assign({}, mvpState.selectedOptions, {
          business_domain: mvpState.analysis.businessDomain,
          pain_points: mvpState.analysis.painPoints,
          system_actions: mvpState.analysis.systemActions,
          scenario_answers: collectScenarioAnswers()
        })
      });
    }catch(error){
      rawResult = app.createFallbackRefineResult(mvpState.original, serializeFastAnalysisForApi(), mvpState.selectedOptions);
      rawResult.mode = 'local-fallback';
      rawResult.error_message = error.message;
    }

    mvpState.analysis.suggestedRequest = String(rawResult.refined_request || mvpState.analysis.suggestedRequest || '').trim();
    mvpState.analysis.rewrittenRequest = String(rawResult.rewritten_request || mvpState.analysis.rewrittenRequest || '').trim();
    mvpState.analysis.targetUsers = normalizeArray(rawResult.target_users).length ? normalizeArray(rawResult.target_users) : mvpState.analysis.targetUsers;
    mvpState.analysis.uncertainItems = normalizeArray(rawResult.uncertain_items).length ? normalizeArray(rawResult.uncertain_items) : mvpState.analysis.uncertainItems;
    mvpState.analysis.optionalAnswers = buildOptionalAnswersFromQuestions(mvpState.analysis.uncertainItems, mvpState.card ? mvpState.card.optional_answers : []);
    // ????????????????????? ITBP ????????
    if(mvpState.deepAnalysisStatus === 'success'){
      mvpState.analysis.structuredReport = normalizeStructuredReport(rawResult.structured_report, mvpState.analysis.structuredReport);
    }
    mvpState.analysis.mode = rawResult.mode || mvpState.analysis.mode;

    renderTagList('uncertainItemList', mvpState.analysis.uncertainItems, '??');
    mvpState.card = buildCardFromState();
    renderDemandCard(mvpState.card);
    document.getElementById('mvp-card-panel').style.display = '';
    document.getElementById('submitOutput').classList.remove('show');
    updateFrontReportFromCard(mvpState.card);

    showMvpStatus('???????????????');
    setButtonLoading('generateDemandBtn', false);
    showAiSuccess('AI ????????????????????');
    document.getElementById('mvp-card-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function applyCardToReport(){
    var card = getEditedCard();

    if(!card.original_request){
      alert('\u8BF7\u5148\u751F\u6210\u5EFA\u8BAE\u7248\u672C');
      return;
    }

    mvpState.card = card;
    updateFrontReportFromCard(card);
    updateHomeDemandPreview(card);
    showMvpStatus('???????????ITBP ??????????????????');

    var preview = document.getElementById('homeDemandPreview');
    if(preview){
      preview.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  function updateDeepReportSections(card){
    var report = card.structured_report || {};
    setText('.orig-text', card.original_request || mvpState.original || '');
    setText('.newreq-sentence', app.summarizeSentence(card));
    setText('.detail-body', makeFrontDetailTextFromCard(card));
    updateBodyValByTag('t-why', escapeHtml(report.why || '?????'));
    updateBodyValByTag('t-what', '<span class="what-red">' + escapeHtml(report.what || '?????') + '</span>');
    updateBodyValByTag('t-wheren', '<b>' + escapeHtml(report.where || '?????') + '</b>');
    updateBodyValByTag('t-who', '<b>' + escapeHtml(report.who || card.target_user || '?????') + '</b>');
    updateBodyValByTag('t-howmuch', escapeHtml(report.howmuch || '?????'));
    updateBodyValByTag('t-how', renderHowStepsHtml(report.how));
    updateBodyValByTag('t-input', escapeHtml(report.input || card.input_data || '?????'));
    updateBodyValByTag('t-output', '<b>???</b>' + escapeHtml(report.output || card.output_result || '?????') + '<br><b>?????</b>' + escapeHtml(card.delivery_method || '?????'));
    updateBodyValByTag('t-monitor', renderMonitorHtml(report.monitor));

    updateSuggestionArea(card);
    updateRoadmap(card);
    updateFlowChart(card);
  }

  async function generateDeepAnalysis(silent){
    var rawResult;
    var report;

    if(!mvpState.analysis){
      if(!silent) alert('?????AI ?????');
      return;
    }
    if(mvpState.deepAnalysisStatus === 'loading'){
      return;
    }

    setDeepAnalysisStatus('loading', 'ITBP????????????????????');
    setDeepSectionsPlaceholder('ITBP????????????????????');
    if(!silent){
      showAiThinking('ITBP?????????????????????');
    }

    try{
      rawResult = await postJson('/api/analyze_deep', {
        user_input: mvpState.original,
        fast_analysis: serializeAnalysisForApi(),
        selected_options: mvpState.selectedOptions
      });
      mvpState.deepAnalysis = rawResult;
      mvpState.deepAnalysisStatus = 'success';
      mvpState.analysis.diagnosis = rawResult.diagnosis || {};
      mvpState.analysis.businessObject = mvpState.analysis.diagnosis.business_object || mvpState.analysis.businessObject;
      mvpState.analysis.currentManualProcess = mvpState.analysis.diagnosis.current_manual_process || mvpState.analysis.currentManualProcess;
      mvpState.analysis.processBreakpoint = mvpState.analysis.diagnosis.process_breakpoint || mvpState.analysis.processBreakpoint;
      mvpState.analysis.passiveConsequence = mvpState.analysis.diagnosis.passive_consequence || mvpState.analysis.passiveConsequence;
      mvpState.analysis.minimumSystemBehavior = normalizeArray(mvpState.analysis.diagnosis.minimum_system_behavior).length ? normalizeArray(mvpState.analysis.diagnosis.minimum_system_behavior) : mvpState.analysis.minimumSystemBehavior;
      // ????????????????????? ITBP ????????
    if(mvpState.deepAnalysisStatus === 'success'){
      mvpState.analysis.structuredReport = normalizeStructuredReport(rawResult.structured_report, mvpState.analysis.structuredReport);
    }
      mvpState.card = buildCardFromState();
      report = mvpState.card.structured_report || {};
      updateDeepReportSections(mvpState.card);
      renderDemandCard(mvpState.card);
      setDeepAnalysisStatus('success', 'ITBP???????????????????????????');
      showAiSuccess('ITBP???????????????????');
    }catch(error){
      mvpState.deepAnalysisStatus = 'error';
      setDeepAnalysisStatus('error', '?????????????????????????');
      setDeepSectionsPlaceholder('?????????????????????????');
      if(!silent){
        showAiError('?????????????????????????');
      }
    }
  }

  function confirmSubmitDemand(){
    var card = getEditedCard();
    var output = document.getElementById('submitOutput');
    var payload;

    if(!card.original_request){
      alert('????????');
      return;
    }

    payload = {
      requirement_type: card.requirement_type,
      original_request: card.original_request,
      rewritten_request: card.rewritten_request,
      domain_name: card.domain_name,
      pain_labels: card.pain_labels,
      action_labels: card.action_labels,
      target_users: card.target_users_list,
      diagnosis: mvpState.analysis ? (mvpState.analysis.diagnosis || {}) : {},
      related_systems: mvpState.analysis ? (mvpState.analysis.relatedSystems || []) : [],
      candidate_systems: mvpState.analysis ? (mvpState.analysis.candidateSystems || []) : [],
      real_intent_guess: card.real_intent_guess,
      refined_request: card.refined_request,
      pending_questions: card.pending_questions,
      optional_answers: card.optional_answers || [],
      answered_clarifications: card.answered_clarifications || [],
      structured_report: card.structured_report,
      selected_constraints: card.selected_constraints,
      scenario_form: mvpState.analysis ? mvpState.analysis.scenarioForm : null,
      scenario_answers: collectScenarioAnswers(),
      selected_options: mvpState.selectedOptions,
      analysis_mode: mvpState.analysis ? mvpState.analysis.mode : 'unknown',
      submit_status: '??????????MVP???',
      created_at: new Date().toLocaleString()
    };

    output.textContent = JSON.stringify(payload, null, 2);
    output.classList.add('show');

    showMvpStatus('???????????ITBP ????????????? ITBP ?????????');
    showAiSuccess('???????? JSON ????');
  }

  function toggleCheck(btn){
    btn.classList.toggle('checked');
    var chk = btn.querySelector('.clarify-ck');
    if(chk) chk.textContent = btn.classList.contains('checked') ? '?' : '';
  }

  function toggleSection(toggleEl, contentId){
    var content = document.getElementById(contentId);
    var arrow = toggleEl.querySelector('.section-toggle-arrow') || toggleEl.querySelector('.body-toggle-arrow');
    var text = toggleEl.querySelector('.section-toggle-text') || toggleEl.querySelector('.body-toggle-text');

    if(!content || !arrow || !text) return;

    if(content.classList.contains('collapsed')){
      content.classList.remove('collapsed');
      arrow.classList.remove('collapsed');
      arrow.textContent = '?';
      text.textContent = '??';
      return;
    }

    content.classList.add('collapsed');
    arrow.classList.add('collapsed');
    arrow.textContent = '?';
    text.textContent = '??';
  }

  function toggleDetail(toggleEl){
    var body = toggleEl.nextElementSibling;
    var arrow = toggleEl.querySelector('.detail-arrow');

    if(body) body.classList.toggle('open');
    if(arrow) arrow.classList.toggle('open');
  }

  app.showMvpStatus = showMvpStatus;

  function scrollToQuickSelection(){
    var quickList = document.getElementById('quickSelectionList');
    if(quickList){
      quickList.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  function switchAppView(viewName){
    var targetView = viewName === 'itbp' || viewName === 'solution' ? viewName : 'submission';
    var targetEl;

    Array.prototype.slice.call(document.querySelectorAll('.app-view')).forEach(function(view){
      var isTarget = view.getAttribute('data-view') === targetView;
      view.hidden = !isTarget;
      if(isTarget){
        targetEl = view;
      }
    });

    Array.prototype.slice.call(document.querySelectorAll('.app-nav-link[data-view-target]')).forEach(function(link){
      link.classList.toggle('active', link.getAttribute('data-view-target') === targetView);
    });

    if(targetView === 'solution'){
      updateSolutionSummary();
    }

    if(targetEl){
      targetEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  function bindAppNavigation(){
    Array.prototype.slice.call(document.querySelectorAll('.app-nav-link[data-view-target]')).forEach(function(link){
      link.addEventListener('click', function(){
        switchAppView(link.getAttribute('data-view-target'));
      });
    });
    switchAppView('submission');
  }

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', bindAppNavigation);
  }else{
    bindAppNavigation();
  }

  global.fillDemoExample = fillDemoExample;
  global.resetMvpDemo = resetMvpDemo;
  global.startClarify = startClarify;
  global.fillQuestionExample = fillQuestionExample;
  global.generateDemandCard = generateDemandCard;
  global.generateDeepAnalysis = generateDeepAnalysis;
  global.applyCardToReport = applyCardToReport;
  global.confirmSubmitDemand = confirmSubmitDemand;
  global.toggleCheck = toggleCheck;
  global.toggleSection = toggleSection;
  global.toggleDetail = toggleDetail;
  global.handleThreeDimInsightChange = handleThreeDimInsightChange;
  global.scrollToQuickSelection = scrollToQuickSelection;
  global.switchAppView = switchAppView;
  global.generateSolutionDraft = generateSolutionDraft;
  global.downloadPrdDocument = downloadPrdDocument;
  global.copyPrdMarkdown = copyPrdMarkdown;
})(window);















