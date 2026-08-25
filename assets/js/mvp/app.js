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
        '<button type="button" class="mvp-ai-popup-close" aria-label="关闭提示">×</button>' +
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
    showAiPopup('thinking', 'AI 正在思考中', message || 'AI 正在根据您的选择思考中，请稍候。');
  }

  function showAiSuccess(message){
    showAiPopup('success', '生成成功', message || 'AI 已生成结果，请查看结果。', 2600);
  }

  function showAiError(message){
    showAiPopup('error', '生成未完成', message || 'AI 生成失败，可稍后重试。', 3200);
  }

  function setButtonLoading(buttonId, isLoading, loadingText){
    var btn = document.getElementById(buttonId);
    if(!btn) return;
    if(isLoading){
      btn.dataset.originalText = btn.dataset.originalText || btn.textContent;
      btn.textContent = loadingText || '生成中...';
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
      box.innerHTML = '<div class="mvp-result-brief"><div class="mvp-result-label">' + escapeHtml(message || 'AI正在生成新版描述...') + '</div><div class="mvp-result-text">你可以继续查看或修改页面其他内容。</div></div>';
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
      button.textContent = mvpState.deepAnalysisStatus === 'loading' ? '生成中...' : '生成 ITBP 深度分析';
    }
  }

  function updateFrontReportFromCard(card){
    // 首页前台按钮只刷新方案页摘要，不再同步写入 ITBP 分析报告。
    updateSolutionSummary();
  }

  function updateHomeDemandPreview(card){
    var preview = document.getElementById('homeDemandPreview');
    if(!preview || !card) return;

    setTextById('homePreviewOriginal', card.original_request || mvpState.original || '待确认');
    setTextById('homePreviewRefined', card.refined_request || card.rewritten_request || app.summarizeSentence(card) || '待确认');
    setTextById('homePreviewPending', card.pending_questions || '暂无明确待确认问题');
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

    setTextById('solutionOriginalRequest', card ? (card.original_request || mvpState.original || '待填写') : '尚未生成需求，请先在业务提需页完成 AI 深挖。');
    setTextById('solutionRefinedRequest', card ? (card.refined_request || card.rewritten_request || '待生成') : '待生成');
    setTextById('solutionDomainObject', card ? ((analysis.businessDomain || card.domain_name || '待识别') + ' / ' + ((analysis.businessObject || (card.diagnosis && card.diagnosis.business_object)) || '待确认业务对象')) : '待识别');
    setTextById('solutionPendingQuestions', card ? (card.pending_questions || (analysis.uncertainItems || []).join('；') || '暂无明确待确认项') : '待识别');
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
    var isInventory = /库存|仓库|缺货|账实|下单/.test(text);
    var isBom = /BOM|图纸|版本|物料|试产/.test(text);
    var isOrder = /订单|发货|交付|经销商|客户催|交期/.test(text);

    if(isInventory){
      return {
        summary: '建议建设“下单前库存可用性校验与缺货预警能力”：整合库存、订单占用和差异状态，在业务下单前校验可用库存，并对缺货或账实差异形成提醒与核查闭环。',
        entry: '业务下单入口 / 销售订单创建页面',
        systems: 'WMS库存、ERP/SAP库存账、订单占用、预留库存、出入库流水',
        modules: ['下单前可用库存校验', '库存不足提醒或拦截规则', '账实差异展示', '仓库核查任务生成', '异常责任人通知与闭环跟踪', '库存校验日志和查询报表'],
        stages: [
          ['阶段1', '确认库存口径、数据源、提醒或拦截规则。'],
          ['阶段2', '梳理 WMS/ERP 库存字段与可用库存计算逻辑。'],
          ['阶段3', '实现下单前校验、缺货提醒和差异展示。'],
          ['阶段4', '选择仓库或业务线试点，跟踪误报和漏报。']
        ],
        risks: ['库存数据本身不准时，单纯前端提醒效果有限。', 'WMS 与 ERP 同步时延会影响可用库存判断。', '直接拦截下单可能影响紧急订单，需要设计例外流程。', '账实差异责任人和关闭标准需要先确认。']
      };
    }
    if(isBom){
      return {
        summary: '建议建设“BOM/图纸变更影响识别与下游确认能力”：在版本变更后自动识别受影响物料、订单、库存和生产计划，并推动采购、生产等责任方确认闭环。',
        entry: 'BOM/图纸版本变更发布节点',
        systems: 'PLM、ERP/SAP、采购订单、生产计划、库存数据',
        modules: ['变更影响范围识别', '新旧版本差异展示', '受影响物料清单', '采购/生产确认待办', '版本一致性校验', '变更处理闭环看板'],
        stages: [
          ['阶段1', '确认变更触发点和影响对象范围。'],
          ['阶段2', '梳理 PLM、ERP、采购和生产数据映射关系。'],
          ['阶段3', '实现影响识别、差异展示和确认待办。'],
          ['阶段4', '试点关键产品线，优化影响规则。']
        ],
        risks: ['BOM层级和替代料规则复杂，影响范围规则需业务确认。', '图纸与BOM版本如果不同步，会影响识别准确性。', '待办过多可能造成信息噪音，需要分级提醒。']
      };
    }
    if(isOrder){
      return {
        summary: '建议建设“订单交付进度可视化与风险预警能力”：集中展示订单从签订、排产、库存齐套、发货到签收的状态，并对延期、缺货和责任节点停滞进行提醒。',
        entry: '销售订单 / 经销商订单跟踪入口',
        systems: '订单系统、ERP/SAP、WMS、MES/计划系统、物流状态',
        modules: ['订单全链路状态看板', '发货与物流状态同步', '延期/缺货预警', '责任人待办生成', '客户反馈口径输出', '异常关闭跟踪'],
        stages: [
          ['阶段1', '确认订单关键节点和责任部门。'],
          ['阶段2', '打通订单、计划、仓库和物流状态。'],
          ['阶段3', '实现进度看板、风险预警和待办推送。'],
          ['阶段4', '按业务线试点，校验状态准确性和提醒有效性。']
        ],
        risks: ['跨系统状态口径可能不一致，需要先定义主口径。', '客户可见信息和内部处理信息需要权限隔离。', '预警阈值过松或过紧都会影响使用体验。']
      };
    }
    return {
      summary: '建议先按“最小可行方案”推进：围绕当前业务断点，明确触发条件、数据来源、责任人和闭环标准，再建设提醒、展示、待办和跟踪能力。',
      entry: '当前业务操作入口',
      systems: '业务主数据、状态数据、责任人数据、处理结果数据',
      modules: ['业务状态集中展示', '异常识别和提醒', '责任人待办', '处理结果跟踪', '管理查询报表'],
      stages: [
        ['阶段1', '确认业务对象、触发条件和成功标准。'],
        ['阶段2', '梳理数据来源和系统承载边界。'],
        ['阶段3', '实现最小闭环功能并试点。'],
        ['阶段4', '根据试点反馈扩展规则和场景。']
      ],
      risks: ['需求边界不清会导致方案过大。', '数据源和责任人未确认会影响落地。', '需要区分系统功能问题和流程管理问题。']
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
      summary: String(draft.executive_summary || draft.summary || '待生成方案摘要。'),
      entry: String(draft.entry_point || draft.entry || '当前业务操作入口'),
      systems: String(draft.data_systems || draft.systems || '待确认数据和系统依赖'),
      modules: normalizeArray(draft.modules).length ? normalizeArray(draft.modules) : ['业务状态集中展示', '异常提醒', '责任人待办', '闭环跟踪'],
      risks: normalizeArray(draft.risks).length ? normalizeArray(draft.risks) : normalizeArray(draft.confirmations),
      stages: stages.map(function(stage, index){
        if(Array.isArray(stage)){
          return [String(stage[0] || ('阶段' + (index + 1))), String(stage[1] || '')];
        }
        return [String((stage && stage.name) || ('阶段' + (index + 1))), String((stage && stage.description) || '')];
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
    if(/质量|质检|检验|不良|缺陷|返工|返修|客诉|8D|NCR|CAPA|抽检|来料检|首检|巡检/.test(text)) return 'quality_control';
    if(/制造|生产执行|车间|工单|报工|MES|设备|停机|工序|节拍|产能|异常停线|返修/.test(text)) return 'manufacturing_execution';
    if(/采购|供应商|交期|催交|到货|采购订单|PO|供应替代|价格|询价|在途/.test(text)) return 'procurement_delivery';
    if(/生产计划|排产|计划调整|临时调整|缺料|齐套|供应链|物料影响|采购在途/.test(text)) return 'plan_material_shortage';
    if(/BOM|图纸|版本|变更|试产|替代料|ECN|ECR/.test(text)) return 'bom_change';
    if(/订单|发货|交付|经销商|客户催|物流|签收|交付风险/.test(text)) return 'order_delivery';
    if(/库存|仓库|账实|可用库存|下单|盘点|库位|WMS/.test(text)) return 'inventory_check';
    if(/主数据|物料主数据|客户主数据|供应商主数据|编码|口径|字段|数据治理/.test(text)) return 'master_data';
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
        '触发：' + pack.trigger + '。',
        '输入：' + pack.inputs.slice(0, 3).join('、') + '。',
        '处理：按' + pack.objectName + '状态、责任人和处理规则生成结果。',
        '输出：' + pack.outputs.slice(0, 2).join('、') + '。'
      ].join('');
      return ['F' + String(index + 1).padStart(2, '0'), moduleName, detail, index < 3 ? 'P0' : 'P1'];
    });
  }

  function prdDomainPack(scenario, ctx){
    var packs = {
      quality_control: {
        title: '质量异常识别与闭环处理 PRD',
        objectName: '质量异常',
        trigger: '来料检、过程检、终检、客诉或巡检发现不良/缺陷',
        roles: ['质量工程师', '检验员', '生产责任人', '供应商质量负责人', 'ITBP'],
        inputs: ['检验单号', '物料/产品编码', '批次/序列号', '不良代码', '缺陷等级', '检验数量', '不良数量', '责任部门', '图片/附件', '处置结论'],
        outputs: ['质量异常单', '不良明细', '责任人待办', '隔离/返工/让步/报废结论', 'CAPA/8D 跟踪状态'],
        defaultModules: ['质量异常创建', '缺陷分类与等级判定', '责任人分派', '处置流程流转', 'CAPA/8D 跟踪', '质量看板与追溯'],
        moduleRules: {
          '质量异常创建': '触发：检验或客诉确认异常。输入检验单、物料、批次、缺陷代码、图片附件。输出质量异常单，并生成唯一异常编号。',
          '缺陷分类与等级判定': '按缺陷代码、影响范围、数量比例和客户影响判定严重等级，等级规则需支持配置。',
          '责任人分派': '根据物料、工序、供应商、产品线或责任部门映射处理人；映射失败进入质量公共池。',
          '处置流程流转': '支持隔离、返工、让步接收、报废、供应商整改等处置动作，并记录审批结论。',
          'CAPA/8D 跟踪': '对重大或重复异常自动生成 CAPA/8D 跟踪项，记录原因分析、纠正措施、预防措施和关闭验证。'
        },
        scopeOut: ['不自动替代质量工程师做最终判责。', '不自动关闭 CAPA/8D，必须保留人工验证。', '不在本期改造检验标准主数据维护流程。'],
        businessFlow: ['检验、生产或客户反馈触发质量异常。', '系统记录异常对象、批次、缺陷、数量和附件。', '系统按规则判定严重等级并分派责任人。', '责任人提交处置动作，必要时发起 CAPA/8D。', '质量人员验证措施有效性后关闭异常。'],
        implementationPlan: ['先选取一个质量场景试点，例如来料检或过程检异常。', '确认缺陷代码、严重等级、责任人映射和处置流程。', '上线异常单、流转、附件、待办和关闭验证。', '扩展到客诉、供应商质量和质量趋势分析。'],
        exceptions: ['缺陷代码缺失时允许暂存，但不能进入自动等级判定。', '批次或序列号缺失时，系统提示追溯范围不完整。', '责任人无法映射时进入质量公共池并提示维护规则。', '同批次重复异常需要提示可能合并处理。'],
        nonFunctional: ['追溯到检验单、批次/序列号、缺陷代码、图片附件和处置记录。', '缺陷等级、责任人映射、CAPA触发条件需要可配置。', '质量附件需要控制访问权限和保留周期。', '重大质量异常的提醒和升级时限需要配置。'],
        acceptance: ['给定一条带缺陷代码的检验异常，系统能生成质量异常单并判定等级。', '责任人规则完整时，异常单能分派到对应责任人并生成待办。', '重大异常能生成 CAPA/8D 跟踪项，并记录关闭验证结果。', '批次查询时能看到异常、处置、责任人和关闭状态。'],
        confirmations: ['缺陷代码和严重等级口径由哪个系统或团队维护？', '哪些异常必须触发 CAPA/8D？', '质量异常关闭需要谁验证？', '供应商质量问题是否需要同步供应商门户？']
      },
      manufacturing_execution: {
        title: '制造执行异常识别与处理闭环 PRD', objectName: '制造执行异常', trigger: '工单执行、工序报工、设备停机或车间异常反馈', roles: ['班组长', '工艺工程师', '生产计划员', '设备负责人', '质量人员'],
        inputs: ['工单号', '工序', '设备', '产线', '计划数量', '报工数量', '不良数量', '停机时长', '异常原因', '责任人'], outputs: ['工单异常单', '停线/延误提醒', '责任人待办', '处理记录', '产线异常看板'],
        defaultModules: ['工单异常采集', '报工差异识别', '停机异常提醒', '责任人待办', '异常处理闭环', '产线看板'], scopeOut: ['不自动调整正式生产计划。', '不替代 MES/设备系统原始采集。', '不自动判定质量责任。'],
        businessFlow: ['车间执行工单并进行工序报工。', '系统识别数量、节拍、设备、质量等异常。', '系统生成异常单并分派给生产、工艺、设备或质量责任人。', '责任人处理并记录原因、措施和恢复时间。', '系统更新工单风险和产线看板。'], implementationPlan: ['选择关键产线和高频异常类型试点。', '确认工单、报工、设备和质量数据口径。', '上线异常识别、待办、处理记录和看板。', '扩展异常分类和产能影响分析。'],
        exceptions: ['设备数据未回传时标记数据滞后。', '报工数量超过计划数量时提示人工确认。', '异常原因未填时不允许关闭。'], nonFunctional: ['追溯到工单、工序、设备、班次和处理记录。', '异常阈值按产线、工序、产品配置。', '车间大屏和移动端需要适配高频操作。'], acceptance: ['报工差异超过阈值时生成异常提醒。', '停机超过阈值时生成设备责任人待办。', '按工单可查看异常处理全过程。'], confirmations: ['异常阈值按什么口径配置？', '停机原因分类由哪个系统维护？', '哪些异常影响工单关闭？']
      },
      procurement_delivery: {
        title: '采购交付风险预警与催交闭环 PRD', objectName: '采购交付风险', trigger: '采购订单临近交期、供应商变更承诺、物料缺口或计划需求变化', roles: ['采购员', '供应链计划', '供应商', '仓库', '生产计划'],
        inputs: ['采购订单号', '物料编码', '供应商', '订单数量', '已收数量', '承诺交期', '需求日期', '在途状态', '替代料', '采购员'], outputs: ['交付风险清单', '催交待办', '供应商回复记录', '缺口影响范围', '到货状态'],
        defaultModules: ['采购订单风险识别', '交期偏差计算', '催交待办', '供应商回复记录', '缺口影响分析', '采购风险看板'], scopeOut: ['不自动修改采购订单。', '不直接代表供应商承诺。', '不替代正式供应商绩效评价。'],
        businessFlow: ['系统定期读取采购订单、需求日期和到货状态。', '系统识别交期偏差、未回复、部分到货和计划需求变化。', '系统生成风险清单并分派给采购员。', '采购员催交并记录供应商回复。', '风险关闭或升级到供应链/生产计划。'], implementationPlan: ['确认采购订单和需求日期主口径。', '配置交期偏差、未回复和缺口风险规则。', '上线风险清单、催交待办和回复记录。', '扩展供应商绩效和预测预警。'],
        exceptions: ['供应商承诺交期为空时标记待催交。', '部分到货但缺口仍影响需求日期时保持风险未关闭。', '采购员为空时进入采购公共池。'], nonFunctional: ['追溯到采购订单、物料、供应商、需求日期和催交记录。', '交期偏差阈值按物料类别和供应商配置。', '供应商回复需保留时间戳和附件。'], acceptance: ['PO 承诺交期晚于需求日期时生成风险。', '采购员催交后能记录供应商回复并更新状态。', '按物料可查看采购在途和缺口影响。'], confirmations: ['需求日期取生产计划还是 MRP 需求？', '供应商回复是否接入门户或邮件？', '风险升级规则是什么？']
      },
      order_delivery: {
        title: '订单交付进度可视化与风险预警 PRD', objectName: '订单交付', trigger: '订单创建、排产、齐套、发货或客户催交', roles: ['销售', '计划', '仓库', '物流', '客服'],
        inputs: ['订单号', '客户', '产品', '承诺交期', '生产状态', '库存齐套', '发货状态', '物流单号'], outputs: ['订单进度看板', '交付风险预警', '客户反馈口径', '责任人待办'], defaultModules: ['订单状态汇总', '交付风险识别', '发货状态同步', '责任人待办', '客户口径输出'], scopeOut: ['不自动承诺新交期。', '不开放内部敏感处理记录给客户。'], businessFlow: ['订单进入系统。', '系统汇总排产、库存、发货和物流状态。', '系统识别延期或状态停滞。', '责任人处理风险并更新客户反馈口径。'], implementationPlan: ['确认订单状态主口径。', '接入计划、仓库和物流状态。', '上线看板和风险待办。', '扩展客户可见口径。'], exceptions: ['跨系统状态冲突时提示人工确认。', '物流状态缺失时标记待补充。'], nonFunctional: ['状态刷新频率需明确。', '内部处理信息和客户可见信息权限隔离。'], acceptance: ['订单延期时生成风险预警。', '按订单可查看全链路状态。', '责任人处理后状态可关闭。'], confirmations: ['订单状态以哪个系统为准？', '客户可见哪些字段？', '交付风险阈值如何定义？']
      },
      inventory_check: {
        title: '库存可用性校验与差异预警 PRD', objectName: '库存可用性', trigger: '下单、领料、调拨、盘点或库存状态变化', roles: ['仓库', '销售', '计划', '供应链', '财务'], inputs: ['物料编码', '仓库', '库位', '现有库存', '可用库存', '占用数量', '冻结数量', '批次'], outputs: ['库存校验结果', '缺货提醒', '账实差异清单', '核查待办'], defaultModules: ['可用库存计算', '下单/领料校验', '账实差异提醒', '仓库核查待办', '库存追溯'], scopeOut: ['不自动调整库存账。', '不替代正式盘点流程。'], businessFlow: ['业务动作触发库存校验。', '系统读取库存、占用、冻结和批次状态。', '系统输出可用性结果和异常提醒。', '仓库核查并关闭差异。'], implementationPlan: ['确认可用库存公式。', '接入 ERP/WMS 库存字段。', '上线校验和差异待办。', '扩展盘点和追溯分析。'], exceptions: ['库存同步超时标记数据滞后。', '批次状态异常时不允许直接判定可用。'], nonFunctional: ['库存判断需展示公式和快照时间。', '按仓库/库位控制权限。'], acceptance: ['库存不足时生成缺货提醒。', '账实差异时生成核查待办。', '可追溯库存快照。'], confirmations: ['可用库存公式是什么？', '库存主口径是 ERP 还是 WMS？', '哪些库存状态不可用？']
      },
      master_data: {
        title: '主数据口径一致性与变更治理 PRD', objectName: '主数据', trigger: '主数据创建、变更、同步失败或跨系统口径不一致', roles: ['数据负责人', '业务负责人', 'ITBP', '系统管理员'], inputs: ['对象编码', '字段值', '来源系统', '目标系统', '变更记录', '同步状态'], outputs: ['主数据差异清单', '同步异常待办', '字段口径说明', '变更审批记录'], defaultModules: ['主数据差异识别', '字段口径校验', '变更审批', '同步状态监控', '异常待办'], scopeOut: ['不自动合并冲突数据。', '不绕过现有主数据审批。'], businessFlow: ['主数据创建或变更。', '系统校验字段完整性和跨系统一致性。', '发现差异后生成待办。', '数据负责人修正并关闭。'], implementationPlan: ['确认主数据对象和字段口径。', '接入源系统和目标系统。', '上线差异清单和同步监控。', '扩展质量评分和治理报表。'], exceptions: ['字段缺失时阻断同步或标记风险。', '多系统值冲突时提示主口径确认。'], nonFunctional: ['字段级变更需留痕。', '差异规则按对象类型配置。'], acceptance: ['字段缺失可被识别。', '跨系统不一致可生成差异待办。', '变更记录可追溯。'], confirmations: ['主数据主口径系统是哪一个？', '哪些字段必须审批？', '同步失败如何重试？']
      }
    };
    return packs[scenario] || {
      title: (ctx.businessObject || '业务需求') + ' PRD', objectName: ctx.businessObject || '业务对象', trigger: '业务动作或异常状态发生', roles: ['业务用户','责任人','ITBP','系统负责人'], inputs: ['业务对象','触发条件','状态','责任人','处理结果'], outputs: ['结果清单','异常提醒','责任人待办','处理记录'], defaultModules: ['状态识别', '规则判断', '结果展示', '责任人待办', '闭环跟踪'], scopeOut: ['不替代人工最终判断。', '不自动写回未确认的核心业务数据。'], businessFlow: ['业务动作触发场景。', '系统读取对象、状态和责任人。', '系统按规则生成结果或异常提醒。', '责任人处理并关闭。'], implementationPlan: ['确认对象、触发条件和规则。', '接入数据源和责任人。', '上线最小闭环功能。', '试点后优化规则和范围。'], exceptions: ['数据缺失时提示补充。', '责任人缺失时进入公共池。', '规则冲突时提示人工确认。'], nonFunctional: ['关键判断需留痕。', '规则和提醒对象需可配置。', '按角色控制可见范围。'], acceptance: ['给定测试数据能生成结果或异常提醒。', '能生成责任人待办并记录处理状态。', '能按对象查询处理全过程。'], confirmations: ctx.pendingList.length ? ctx.pendingList : ['触发条件是什么？', '数据来源以哪个系统为准？', '关闭标准是什么？']
    };
  }

  function prdSpecForScenario(scenario, ctx){
    var pack = prdDomainPack(scenario, ctx);
    var functions = makeFunctionRows(ctx.modules, pack);
    var scopeIn = uniquePrdList(ctx.modules).length ? uniquePrdList(ctx.modules) : uniquePrdList(pack.defaultModules);
    return {
      title: pack.title,
      objectives: [
        '当' + pack.trigger + '时，系统能围绕' + pack.objectName + '自动识别影响范围、状态或风险。',
        '形成' + pack.outputs.slice(0, 3).join('、') + '，让' + pack.roles.slice(0, 3).join('、') + '在同一口径下处理。',
        '将依赖人工询问、线下确认或事后补救的动作前移为系统提醒、待办和闭环跟踪。'
      ],
      scopeIn: scopeIn.map(function(item){ return '建设' + item + '能力，明确触发条件、输入字段、处理规则、输出结果和责任人。'; }),
      scopeOut: pack.scopeOut,
      businessFlow: pack.businessFlow,
      implementationPlan: pack.implementationPlan,
      functions: functions,
      dataRows: pack.inputs.slice(0, 8).map(function(item, index){ return [index === 0 ? pack.objectName + '主对象' : '输入字段' + index, item, '来源系统/主口径需确认']; }).concat(pack.outputs.slice(0, 5).map(function(item){ return ['输出结果', item, '本需求生成或更新']; })),
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
    var pending = card.pending_questions || normalizeArray(analysis.uncertainItems).join('；') || '';
    var ctx = {
      businessObject: analysis.businessObject || (card.diagnosis && card.diagnosis.business_object) || report.what || '业务需求',
      modules: normalizeArray(draft.modules),
      pendingList: pending ? pending.split(/[；;\n]/).map(function(item){ return item.trim(); }).filter(Boolean) : []
    };
    var spec = prdSpecForScenario(inferPrdScenario(textForScenario), ctx);
    var today = new Date().toISOString().slice(0, 10);
    var refined = card.refined_request || card.rewritten_request || analysis.rewrittenRequest || analysis.suggestedRequest || card.original_request || mvpState.original || '待确认';
    var original = card.original_request || mvpState.original || '待确认';
    var targetUsers = card.target_user || report.who || normalizeArray(analysis.targetUsers).join('、') || '待确认';
    var domain = [analysis.businessDomain || card.domain_name, analysis.businessObject || (card.diagnosis && card.diagnosis.business_object)].filter(Boolean).join(' / ') || '待确认';

    return [
      '# ' + spec.title,
      '',
      '## 1. 文档信息',
      '',
      '| 字段 | 内容 |',
      '| --- | --- |',
      '| 文档类型 | PRD 产品需求文档草案 |',
      '| 生成日期 | ' + today + ' |',
      '| 输出对象 | ' + (collectSolutionSettings().output_style || 'ITBP 内部评估版') + ' |',
      '| 业务域 / 对象 | ' + domain + ' |',
      '| 文档状态 | AI 生成草案，需业务、ITBP、系统负责人共同确认 |',
      '',
      '## 2. 需求背景',
      '',
      original,
      '',
      '## 3. AI 改写后的需求',
      '',
      refined,
      '',
      '## 4. 当前业务问题',
      '',
      markdownList(normalizeArray(analysis.painPoints), report.why || '当前问题需要业务补充具体发生频率、影响范围和责任部门。'),
      '',
      '## 5. 业务目标',
      '',
      markdownList(spec.objectives),
      '',
      '## 6. 目标用户与角色',
      '',
      '- 主要用户：' + targetUsers,
      '- 计划/业务责任人：确认触发条件、处理规则和关闭标准。',
      '- ITBP：确认系统边界、数据口径、实施优先级和验收方式。',
      '- 系统/数据负责人：确认接口、字段、同步频率和权限范围。',
      '',
      '## 7. 需求范围',
      '',
      '### 7.1 本期范围',
      '',
      markdownList(spec.scopeIn),
      '',
      '### 7.2 暂不纳入范围',
      '',
      markdownList(spec.scopeOut),
      '',
      '## 8. 功能需求',
      '',
      '| 编号 | 功能模块 | 具体规则 / 交互 / 输出 | 优先级 |',
      '| --- | --- | --- | --- |',
      spec.functions.map(function(row){ return '| ' + row[0] + ' | ' + row[1] + ' | ' + row[2] + ' | ' + row[3] + ' |'; }).join('\n'),
      '',
      '## 9. 业务流程说明',
      '',
      spec.businessFlow.map(function(step, index){ return (index + 1) + '. ' + step; }).join('\n'),
      '',
      '## 10. 数据输入与输出',
      '',
      '| 数据对象 | 关键字段 / 口径 | 来源 / 说明 |',
      '| --- | --- | --- |',
      spec.dataRows.map(function(row){ return '| ' + row[0] + ' | ' + row[1] + ' | ' + row[2] + ' |'; }).join('\n'),
      '',
      '## 11. 权限与角色',
      '',
      '- 业务用户：查看与本人业务范围相关的需求、清单、风险和处理结果。',
      '- 责任人：接收待办、填写处理动作、维护预计完成时间、关闭异常。',
      '- ITBP：维护 PRD 基线、确认功能边界、组织评审和验收。',
      '- 管理层：查看汇总风险、逾期待办、关闭率和趋势，不直接修改业务处理记录。',
      '',
      '## 12. 异常场景',
      '',
      markdownList(spec.exceptions),
      '',
      '## 13. 非功能需求',
      '',
      markdownList(spec.nonFunctional),
      '',
      '## 14. 验收标准',
      '',
      markdownList(spec.acceptance),
      '',
      '## 15. 上线与实施建议',
      '',
      spec.implementationPlan.map(function(step, index){ return (index + 1) + '. ' + step; }).join('\n'),
      '',
      '## 16. 待确认问题',
      '',
      markdownList(spec.confirmations),
      '',
      '## 17. 备注',
      '',
      '- 第 9 章描述业务实际流转，第 15 章描述项目实施节奏，两者不得互相复制。',
      '- 第 12 章仅写系统运行中可能遇到的异常，第 16 章仅写立项/设计前必须向业务确认的问题。',
      '- 本 PRD 为 AI 草案，不代表最终立项结论。公开网络资料只能作为通用经验，不能直接视为公司内部事实。'
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
      alert('请先生成 PRD 文档。');
      return;
    }
    if(downloadBtn){
      downloadBtn.dataset.originalText = downloadBtn.dataset.originalText || downloadBtn.textContent;
      downloadBtn.textContent = '正在准备下载...';
      downloadBtn.disabled = true;
      downloadBtn.classList.add('loading');
    }
    try{
      var title = (markdown.split('\n')[0] || 'PRD文档').replace(/^#\s*/, '').replace(/[\\/:*?"<>|]/g, '_');
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
      showAiSuccess('PRD Word 文档已开始下载。');
    }finally{
      if(downloadBtn){
        downloadBtn.textContent = downloadBtn.dataset.originalText || '下载 Word (.doc)';
        downloadBtn.disabled = false;
        downloadBtn.classList.remove('loading');
      }
    }
  }

  async function copyPrdMarkdown(){
    var markdown = mvpState.prdMarkdown;
    if(!markdown){
      alert('请先生成 PRD 文档。');
      return;
    }
    try{
      await navigator.clipboard.writeText(markdown);
      showAiSuccess('PRD Markdown 已复制，可粘贴到文档工具中继续编辑。');
    }catch(error){
      alert('复制失败，请使用下载功能。');
    }
  }
  function collectSolutionSettings(){
    var depth = document.getElementById('solutionDepth');
    var type = document.getElementById('solutionType');
    var style = document.getElementById('solutionStyle');
    var webSearch = document.getElementById('solutionWebSearch');
    return {
      depth: depth ? depth.value : '标准方案',
      solution_type: type ? type.value : '综合方案',
      output_style: style ? style.value : 'ITBP 内部评估版',
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
      alert('请先在“业务提需”页输入需求并完成 AI 深挖。');
      switchAppView('submission');
      return;
    }

    if(status){
      status.textContent = '生成中';
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
      btn.textContent = 'AI 正在生成 PRD...';
      btn.disabled = true;
      btn.classList.add('loading');
    }
    showAiThinking('AI 正在根据业务需求、澄清结果和 ITBP 诊断生成 PRD 文档，请稍候。');

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
      status.textContent = rawResult.mode === 'llm' ? '已生成 PRD' : '已生成 PRD 草案';
      status.className = 'solution-status ready';
    }
    if(btn){
      btn.textContent = btn.dataset.originalText || '生成 PRD 文档';
      btn.disabled = false;
      btn.classList.remove('loading');
    }
    showAiSuccess('PRD 文档已生成，请查看下方预览或下载文档。');
  }

  function setDeepSectionsPlaceholder(message){
    var text = message || '深度诊断尚未生成。业务人员可以先确认提交，ITBP可在后台生成完整分析。';
    updateBodyValByTag('t-why', escapeHtml(text));
    updateBodyValByTag('t-what', '<span class="what-red">待生成</span>');
    updateBodyValByTag('t-wheren', '<b>待生成</b>');
    updateBodyValByTag('t-who', '<b>待生成</b>');
    updateBodyValByTag('t-howmuch', '待业务确认');
    updateBodyValByTag('t-how', renderHowStepsHtml([text]));
    updateBodyValByTag('t-input', escapeHtml('待深度分析生成'));
    updateBodyValByTag('t-output', '<b>输出：</b>' + escapeHtml('待深度分析生成'));
    updateBodyValByTag('t-monitor', renderMonitorHtml(['待深度分析生成']));

    if(document.querySelector('.sug-focus')){
      document.querySelector('.sug-focus').innerHTML = renderDiagnosisListItem('#e53935', 'i', 'ITBP诊断摘要', text);
    }
    if(document.querySelector('.sug-act')){
      document.querySelector('.sug-act').innerHTML = renderDiagnosisListItem('#1a73e8', 'i', '系统替代与待确认', text);
    }
    Array.prototype.slice.call(document.querySelectorAll('.linear-roadmap .lr-ms-title')).forEach(function(node){
      node.textContent = '待生成';
    });
    Array.prototype.slice.call(document.querySelectorAll('.flow .flow-n')).forEach(function(node){
      var label = node.querySelector('.flow-lb');
      if(label){
        node.innerHTML = '<span class="flow-lb">' + label.textContent + '</span>' + escapeHtml('待生成');
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
    typeBox.textContent = 'AI 初步判断：' + (typeName || '通用业务需求');
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
      采购: 'procurement',
      财务: 'finance',
      HR: 'hr',
      法务: 'legal',
      仓储: 'warehouse',
      生产: 'production',
      销售: 'sales',
      通用: 'general',
      待业务确认: 'general'
    };

    return aliases[normalized] || findCodeByName(app.getDomainOptions(), normalized, 'general');
  }

  function formatListText(items, emptyText){
    return items && items.length ? items.join('、') : (emptyText || '待确认');
  }

  function formatPendingText(items){
    return items && items.length ? items.join('；') : '暂无';
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
      why: String(source.why || base.why || '待业务确认').trim() || '待业务确认',
      what: String(source.what || base.what || '待业务确认').trim() || '待业务确认',
      where: String(source.where || base.where || '待业务确认').trim() || '待业务确认',
      who: String(source.who || base.who || '待业务确认').trim() || '待业务确认',
      input: String(source.input || base.input || '待业务确认').trim() || '待业务确认',
      output: String(source.output || base.output || '待业务确认').trim() || '待业务确认',
      how: normalizeArray(source.how).length ? normalizeArray(source.how) : (normalizeArray(base.how).length ? normalizeArray(base.how) : ['待业务确认']),
      monitor: normalizeArray(source.monitor).length ? normalizeArray(source.monitor) : (normalizeArray(base.monitor).length ? normalizeArray(base.monitor) : ['待业务确认']),
      howmuch: String(source.howmuch || base.howmuch || '待业务确认').trim() || '待业务确认'
    };
  }

  function shortText(value, limit){
    var text = String(value || '').trim();
    if(!text) return '待确认';
    if(text.length <= limit){
      return text;
    }
    return text.slice(0, limit) + '...';
  }

  function buildThreeDimSummaryFromInsight(insight){
    return '业务域：' + insight.domain.name + '｜痛点类型：' + formatListText((insight.pains || []).map(function(item){ return item.name; }), '待确认') + '｜系统动作：' + formatListText((insight.actions || []).map(function(item){ return item.name; }), '待确认');
  }

  function buildAnalysisText(analysis){
    return 'AI 判断这更接近【' + analysis.businessDomain + '】场景，主要问题是【' + formatListText(analysis.painPoints, '待确认') + '】，希望系统支持【' + formatListText(analysis.systemActions, '待确认') + '】。';
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
      parts.push('影响对象：' + roles.join('、'));
    }
    if(focusPoints.length){
      parts.push('关注重点：' + focusPoints.join('、'));
    }
    if(expectations.length){
      parts.push('系统期望：' + expectations.join('、'));
    }

    return parts.length ? parts.join('｜') : '尚未选择，当前按 AI 初步判断生成。';
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
      .replace(/^是否/, '')
      .replace(/例如.*/, '')
      .replace(/作为.*/, '')
      .replace(/[。！？!?；;]/g, '')
      .trim();

    if(label.indexOf('，') > -1 || label.indexOf(',') > -1 || label.indexOf('、') > -1){
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
    var roleLike = /供应链|采购|仓库|车间|计划|质量|售后|客服|责任人|管理层|ITBP|供应商/;
    var result = [];
    var seen = {};

    function addLabel(label){
      if(!label || seen[label]) return;
      seen[label] = true;
      result.push(label);
    }

    normalizeArray(rawValues).forEach(function(value){
      var parts = group === 'affected_roles'
        ? String(value).split(/[、,，/]/).map(function(item){ return item.trim(); }).filter(Boolean)
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
      .replace(/[。！？!?；;]/g, '')
      .replace(/^(是否|需要|需|本次需求|当前|希望|系统|自动|支持|实现)/, '')
      .replace(/^(优先解决|主要关注|重点关注)/, '')
      .replace(/(是否|需要|需|相关的|相关|问题|风险|信息|数据)$/g, '')
      .trim();
  }

  function optionLabelByKeywords(value, group){
    var text = compactText(value);
    var rules = {
      affected_roles: [
        ['计划人员,计划员,生产计划,计划', '计划'],
        ['供应链负责人,供应链,供应', '供应链'],
        ['采购执行,采购团队,采购', '采购'],
        ['车间主管,车间,产线', '车间'],
        ['责任人,负责人', '责任人'],
        ['质量专员,质量', '质量'],
        ['仓库管理员,仓库', '仓库'],
        ['售后专员,售后,客服,客户', '售后'],
        ['供应商', '供应商'],
        ['ITBP,IT', 'ITBP']
      ],
      focus_points: [
        ['看不到,不可见,不知道,不清楚,不透明', '看不见'],
        ['缺料,物料不足', '缺料'],
        ['晚发现,才发现,提前判断,预判', '晚发现'],
        ['影响范围,范围', '范围不清'],
        ['人工,询问,问,追,催', '靠人问'],
        ['闭环,关闭,未处理', '无闭环'],
        ['库存,在途,订单,交期,口径', '口径不清'],
        ['超期,延期,滞后,不及时', '超期滞后'],
        ['状态,进度,做到哪一步', '状态不清'],
        ['责任人,责任', '责任不清']
      ],
      system_expectations: [
        ['分析,影响分析,评估', '分析影响'],
        ['清单,列表,输出,生成', '生成清单'],
        ['识别,判断,原因,分类', '识别风险'],
        ['提醒,推送,待办,通知', '推送待办'],
        ['跟踪,闭环,关闭,处理状态', '跟踪闭环'],
        ['同步,更新', '自动同步'],
        ['展示,查看,看板,查询', '展示数据'],
        ['拦截,控制,校验', '自动控制']
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
      .replace(/^是否/, '')
      .replace(/[，,].*$/, '')
      .replace(/例如.*/, '')
      .replace(/作为.*/, '')
      .trim();

    if(label.length > 8){
      label = label.slice(0, 8);
    }
    if(!label){
      label = rawValue.slice(0, 8) || '待确认';
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
    input.value = '采购交付压力很大，每次都要人工算BOM用量，能不能让SAP自动算好并发给采购执行？';
    showMvpStatus('已填入示例，点击“AI 深挖需求”即可。');
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
    setDeepAnalysisStatus('idle', '深度诊断尚未生成。业务人员可以先确认提交，ITBP可在后台生成完整分析。');

    showMvpStatus('已恢复初始状态。');
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
      container.innerHTML = '<span class="mvp-tag muted">' + escapeHtml(emptyText || '暂无') + '</span>';
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
      hint.textContent = (form.template_name || '场景化澄清表') + (form.match_reason ? '｜' + form.match_reason : '');
    }
    box.innerHTML = form.groups.map(function(group){
      var options = Array.isArray(group.options) ? group.options : [];
      return '<div class="mvp-choice-card">' +
        '<div class="mvp-choice-title">' + escapeHtml(group.title || '请补充确认') + (group.required ? ' <span class="mvp-source pending">建议选</span>' : '') + '</div>' +
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
    // 收集澄清项数据
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

    renderTagList('uncertainItemList', mvpState.analysis ? mvpState.analysis.uncertainItems : [], '待确认');
  }

  function buildSuccessMetric(analysis){
    var report = mvpState.deepAnalysisStatus === 'success' ? (analysis.structuredReport || {}) : {};
    var monitor = normalizeArray(report.monitor);
    if(monitor.length){
      return monitor.join('；');
    }

    var domainName = analysis.businessDomain === '通用' ? '相关业务' : analysis.businessDomain;
    return domainName + '场景的处理更及时、更准确、更省人工。';
  }

  function buildCardFromState(){
    var analysis = mvpState.analysis;
    var selected = mvpState.selectedOptions;
    var deepReady = mvpState.deepAnalysisStatus === 'success';
    var report = deepReady ? (analysis.structuredReport || normalizeStructuredReport()) : normalizeStructuredReport({
      why: formatListText(analysis.painPoints, '待业务确认'),
      what: analysis.suggestedRequest || analysis.rewrittenRequest || '待业务确认',
      who: formatListText(analysis.targetUsers, '待业务确认'),
      input: '待业务确认',
      output: formatListText(analysis.systemActions, '待业务确认'),
      how: ['待点击生成ITBP深度分析'],
      monitor: ['待点击生成ITBP深度分析']
    });
    var targetUsers = normalizeArray(selected.affected_roles).length ? normalizeArray(selected.affected_roles) : normalizeArray(analysis.targetUsers);
    var focusPoints = normalizeArray(selected.focus_points);
    var expectations = normalizeArray(selected.system_expectations);
    var diagnosis = deepReady ? Object.assign({}, analysis.diagnosis || {}) : {};

    diagnosis.business_object = diagnosis.business_object || (deepReady ? analysis.businessObject : '') || '待点击生成ITBP深度分析';
    diagnosis.current_manual_process = diagnosis.current_manual_process || (deepReady ? analysis.currentManualProcess : '') || diagnosis.current_process || '待点击生成ITBP深度分析';
    diagnosis.current_process = diagnosis.current_process || diagnosis.current_manual_process;
    diagnosis.process_breakpoint = diagnosis.process_breakpoint || (deepReady ? analysis.processBreakpoint : '') || '待点击生成ITBP深度分析';
    diagnosis.passive_consequence = diagnosis.passive_consequence || (deepReady ? analysis.passiveConsequence : '') || diagnosis.business_impact || '待点击生成ITBP深度分析';
    diagnosis.business_impact = diagnosis.business_impact || diagnosis.passive_consequence;
    diagnosis.minimum_system_behavior = normalizeArray(diagnosis.minimum_system_behavior).length ? normalizeArray(diagnosis.minimum_system_behavior) : (deepReady ? normalizeArray(analysis.minimumSystemBehavior) : ['待点击生成ITBP深度分析']);
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
      pain_point: report.why || formatListText(analysis.painPoints, '待业务确认'),
      target_user: formatListText(targetUsers, report.who || '待业务确认'),
      system_action: formatListText(analysis.systemActions, '待确认'),
      input_data: report.input || formatListText(focusPoints, '待业务确认'),
      output_result: report.output || formatListText(expectations, '待业务确认'),
      delivery_method: expectations.length ? expectations.join('、') : '待业务确认',
      success_metric: buildSuccessMetric(analysis),
      domain_name: analysis.businessDomain,
      pain_labels: formatListText(analysis.painPoints, '待确认'),
      action_labels: formatListText(analysis.systemActions, '待确认'),
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
    var safeSteps = normalizeArray(steps).length ? normalizeArray(steps) : ['待业务确认'];

    return '<div class="how-steps">' + safeSteps.map(function(step, index){
      return '<div class="how-step"><b>S' + (index + 1) + '</b><br>' + escapeHtml(step) + '</div>';
    }).join('') + '</div>';
  }

  function renderMonitorHtml(items){
    var safeItems = normalizeArray(items).length ? normalizeArray(items) : ['待业务确认'];

    return '<div class="mon-steps">' + safeItems.map(function(item, index){
      var cls = index === safeItems.length - 1 ? 'mon-step mon-result' : 'mon-step';
      var label = index === safeItems.length - 1 ? '结果' : ('过程' + (index + 1));
      return '<div class="' + cls + '"><b>' + label + '</b><br>' + escapeHtml(item) + '</div>';
    }).join('') + '</div>';
  }

  function formatDiagnosisList(values, emptyText){
    return normalizeArray(values).length ? normalizeArray(values).join('、') : (emptyText || '待业务确认');
  }

  function renderDiagnosisListItem(color, number, title, value){
    return '<li><span class="sug-nb" style="background:' + color + '">' + number + '</span><b>' + escapeHtml(title) + '：</b>' + escapeHtml(value || '待业务确认') + '</li>';
  }

  function renderInlineTags(items, emptyText){
    var values = normalizeArray(items);
    if(!values.length){
      return '<span class="mvp-tag muted">' + escapeHtml(emptyText || '暂无') + '</span>';
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
      how.length ? how.join(' → ') : '待业务确认',
      report.why,
      report.where,
      report.who,
      report.output,
      monitor.length ? monitor.join(' · ') : '待业务确认'
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
        renderDiagnosisListItem('#e53935', '1', '业务对象', diagnosis.business_object || '待业务确认') +
        renderDiagnosisListItem('#e53935', '2', '当前人工做法', diagnosis.current_manual_process || diagnosis.current_process || report.where) +
        renderDiagnosisListItem('#e53935', '3', '流程断点', diagnosis.process_breakpoint) +
        renderDiagnosisListItem('#e53935', '4', '被动后果', diagnosis.passive_consequence || diagnosis.business_impact);
    }

    if(actList){
      actList.innerHTML =
        renderDiagnosisListItem('#1a73e8', '1', '系统最小动作', formatDiagnosisList(diagnosis.minimum_system_behavior || diagnosis.desired_system_behavior, report.output)) +
        renderDiagnosisListItem('#1a73e8', '2', '深度诊断', diagnosis.pain_root_cause || report.why) +
        renderDiagnosisListItem('#1a73e8', '3', '待确认项', card.pending_questions || formatDiagnosisList(diagnosis.uncertain_items)) +
        renderDiagnosisListItem('#1a73e8', '✓', '建议提交版本', card.refined_request || '待确认');
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
    showMvpStatus('AI 三维判断已更新，点击“根据选择优化”可生成新的建议版本。');
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
      throw new Error(data.error || ('请求失败：' + response.status));
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
      alert('请先输入一句需求描述');
      if(inputEl) inputEl.focus();
      return;
    }

    showMvpStatus('AI 正在快速生成前台需求...');
    showAiThinking('AI 正在快速生成新版需求，不影响你继续操作页面。');
    setButtonLoading('startClarifyBtn', true, '生成中...');
    renderCardLoading('AI正在生成新版描述...');
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
    setDeepAnalysisStatus('idle', '深度诊断尚未生成。业务人员可以先确认提交，ITBP可在后台生成完整分析。');

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
    setDeepAnalysisStatus('idle', '深度诊断尚未生成。业务人员可以先确认提交，ITBP可在后台生成完整分析。');

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
      ? 'AI 已完成深挖。你只需要点选几项，再做轻微修改即可。'
      : '当前使用 mock 结果完成深挖。你只需要点选几项，再做轻微修改即可。';

    showMvpStatus(modeMessage);
    setButtonLoading('startClarifyBtn', false);
    showAiSuccess('AI 已完成前台需求生成，请查看新版描述和快速确认项。');
    document.getElementById('mvp-clarify-panel').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function fillQuestionExample(){
    var analysis = mvpState.analysis;

    if(!analysis){
      alert('请先点击“AI 深挖需求”');
      return;
    }

    mvpState.selectedOptions = {
      affected_roles: (analysis.confirmationOptions.affected_roles || []).slice(0, 2),
      focus_points: (analysis.confirmationOptions.focus_points || []).slice(0, 2),
      system_expectations: (analysis.confirmationOptions.system_expectations || []).slice(0, 2),
      scenario_answers: collectScenarioAnswers()
    };

    renderQuickSelections(analysis.confirmationOptions, mvpState.selectedOptions);
    showMvpStatus('已快速选中示例项。');
  }

  async function generateDemandCard(){
    var rawResult;

    if(!mvpState.analysis){
      alert('请先点击“AI 深挖需求”');
      return;
    }

    mvpState.selectedOptions = collectSelectedOptions();
    mvpState.selectedOptions.scenario_answers = collectScenarioAnswers();
    showMvpStatus('AI 正在根据你的选择优化建议版本...');
    showAiThinking('AI 正在根据您的选择优化新版需求，请稍候。');
    setButtonLoading('generateDemandBtn', true, '优化中...');

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
    // 首页优化只更新可提交需求，不提前生成或刷新 ITBP 深度分析页内容。
    if(mvpState.deepAnalysisStatus === 'success'){
      mvpState.analysis.structuredReport = normalizeStructuredReport(rawResult.structured_report, mvpState.analysis.structuredReport);
    }
    mvpState.analysis.mode = rawResult.mode || mvpState.analysis.mode;

    renderTagList('uncertainItemList', mvpState.analysis.uncertainItems, '暂无');
    mvpState.card = buildCardFromState();
    renderDemandCard(mvpState.card);
    document.getElementById('mvp-card-panel').style.display = '';
    document.getElementById('submitOutput').classList.remove('show');
    updateFrontReportFromCard(mvpState.card);

    showMvpStatus('建议提交版本已按你的选择优化。');
    setButtonLoading('generateDemandBtn', false);
    showAiSuccess('AI 已根据您的选择优化完成，请查看新版需求。');
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
    showMvpStatus('已同步到首页确认预览。ITBP 分析不会自动更新，需要单独点击生成。');

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
    updateBodyValByTag('t-why', escapeHtml(report.why || '待业务确认'));
    updateBodyValByTag('t-what', '<span class="what-red">' + escapeHtml(report.what || '待业务确认') + '</span>');
    updateBodyValByTag('t-wheren', '<b>' + escapeHtml(report.where || '待业务确认') + '</b>');
    updateBodyValByTag('t-who', '<b>' + escapeHtml(report.who || card.target_user || '待业务确认') + '</b>');
    updateBodyValByTag('t-howmuch', escapeHtml(report.howmuch || '待业务确认'));
    updateBodyValByTag('t-how', renderHowStepsHtml(report.how));
    updateBodyValByTag('t-input', escapeHtml(report.input || card.input_data || '待业务确认'));
    updateBodyValByTag('t-output', '<b>输出：</b>' + escapeHtml(report.output || card.output_result || '待业务确认') + '<br><b>交付方式：</b>' + escapeHtml(card.delivery_method || '待业务确认'));
    updateBodyValByTag('t-monitor', renderMonitorHtml(report.monitor));

    updateSuggestionArea(card);
    updateRoadmap(card);
    updateFlowChart(card);
  }

  async function generateDeepAnalysis(silent){
    var rawResult;
    var report;

    if(!mvpState.analysis){
      if(!silent) alert('请先点击“AI 深挖需求”');
      return;
    }
    if(mvpState.deepAnalysisStatus === 'loading'){
      return;
    }

    setDeepAnalysisStatus('loading', 'ITBP深度分析正在生成中，你可以继续操作页面。');
    setDeepSectionsPlaceholder('ITBP深度分析正在生成中，你可以继续操作页面。');
    if(!silent){
      showAiThinking('ITBP深度分析正在后台生成，你可以继续操作页面。');
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
      // 首页优化只更新可提交需求，不提前生成或刷新 ITBP 深度分析页内容。
    if(mvpState.deepAnalysisStatus === 'success'){
      mvpState.analysis.structuredReport = normalizeStructuredReport(rawResult.structured_report, mvpState.analysis.structuredReport);
    }
      mvpState.card = buildCardFromState();
      report = mvpState.card.structured_report || {};
      updateDeepReportSections(mvpState.card);
      renderDemandCard(mvpState.card);
      setDeepAnalysisStatus('success', 'ITBP深度分析已生成，可查看下方结构化分析、路线图和流程图。');
      showAiSuccess('ITBP深度分析已生成，请查看下方结构化分析。');
    }catch(error){
      mvpState.deepAnalysisStatus = 'error';
      setDeepAnalysisStatus('error', '深度分析生成失败，可稍后重试，不影响当前需求提交。');
      setDeepSectionsPlaceholder('深度分析生成失败，可稍后重试，不影响当前需求提交。');
      if(!silent){
        showAiError('深度分析生成失败，可稍后重试，不影响当前需求提交。');
      }
    }
  }

  function confirmSubmitDemand(){
    var card = getEditedCard();
    var output = document.getElementById('submitOutput');
    var payload;

    if(!card.original_request){
      alert('请先生成建议版本');
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
      submit_status: '业务人员已确认提交（MVP演示）',
      created_at: new Date().toLocaleString()
    };

    output.textContent = JSON.stringify(payload, null, 2);
    output.classList.add('show');

    showMvpStatus('已生成精简版提交内容。ITBP 深度分析未自动触发，可切到 ITBP 分析页后手动生成。');
    showAiSuccess('需求已提交，精简 JSON 已生成。');
  }

  function toggleCheck(btn){
    btn.classList.toggle('checked');
    var chk = btn.querySelector('.clarify-ck');
    if(chk) chk.textContent = btn.classList.contains('checked') ? '✓' : '';
  }

  function toggleSection(toggleEl, contentId){
    var content = document.getElementById(contentId);
    var arrow = toggleEl.querySelector('.section-toggle-arrow') || toggleEl.querySelector('.body-toggle-arrow');
    var text = toggleEl.querySelector('.section-toggle-text') || toggleEl.querySelector('.body-toggle-text');

    if(!content || !arrow || !text) return;

    if(content.classList.contains('collapsed')){
      content.classList.remove('collapsed');
      arrow.classList.remove('collapsed');
      arrow.textContent = '▼';
      text.textContent = '收起';
      return;
    }

    content.classList.add('collapsed');
    arrow.classList.add('collapsed');
    arrow.textContent = '►';
    text.textContent = '展开';
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















