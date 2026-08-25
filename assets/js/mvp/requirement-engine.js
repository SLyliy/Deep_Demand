(function(global){
  var app = global.DeepDemandMvp = global.DeepDemandMvp || {};
  var requirementTypes = app.requirementTypes || {};
  var requirementTypeOrder = app.requirementTypeOrder || [];
  var defaultType = app.defaultRequirementType || 'general';
  var DOMAIN_CONFIG = app.DOMAIN_CONFIG || {};
  var DOMAIN_ORDER = app.DOMAIN_ORDER || [];
  var PAIN_CONFIG = app.PAIN_CONFIG || {};
  var PAIN_ORDER = app.PAIN_ORDER || [];
  var ACTION_CONFIG = app.ACTION_CONFIG || {};
  var ACTION_ORDER = app.ACTION_ORDER || [];
  var PAIN_INFERENCE_RULES = app.PAIN_INFERENCE_RULES || [];
  var QUESTION_CONFIG = app.THREE_DIMENSION_QUESTION_CONFIG || {};

  function normalizeText(input){
    return String(input || '').trim();
  }

  function normalizeAnswer(value){
    var text = String(value || '').trim();
    return text || '待确认';
  }

  function createOptions(config, order){
    return (order || []).map(function(code){
      return Object.assign({ code: code }, config[code] || {});
    });
  }

  var domainOptions = createOptions(DOMAIN_CONFIG, DOMAIN_ORDER);
  var painOptions = createOptions(PAIN_CONFIG, PAIN_ORDER);
  var actionOptions = createOptions(ACTION_CONFIG, ACTION_ORDER);

  function getTypeDefinition(type){
    return requirementTypes[type] || requirementTypes[defaultType];
  }

  function getOptionByCode(options, code, fallbackCode){
    var found = (options || []).find(function(option){
      return option.code === code;
    });

    if(found) return found;
    if(typeof fallbackCode === 'undefined') return null;

    return (options || []).find(function(option){
      return option.code === fallbackCode;
    }) || null;
  }

  function scoreKeywords(text, keywords){
    return (keywords || []).reduce(function(total, keyword){
      return total + (text.indexOf(keyword) > -1 ? keyword.length : 0);
    }, 0);
  }

  function detectSingleByConfig(text, options, fallbackCode){
    var best = { score: 0, option: getOptionByCode(options, fallbackCode, fallbackCode) };

    (options || []).forEach(function(option){
      var score = scoreKeywords(text, option.keywords);
      if(score > best.score){
        best = { score: score, option: option };
      }
    });

    return best.option || getOptionByCode(options, fallbackCode, fallbackCode);
  }

  function detectMultiByConfig(text, options){
    return (options || []).map(function(option){
      return {
        option: option,
        score: scoreKeywords(text, option.keywords)
      };
    }).filter(function(item){
      return item.score > 0;
    }).sort(function(a, b){
      return b.score - a.score;
    }).map(function(item){
      return item.option;
    });
  }

  function uniqueCodes(codes){
    return (codes || []).filter(function(code, index, list){
      return code && list.indexOf(code) === index;
    });
  }

  function mapCodesToOptions(codes, options){
    return uniqueCodes(codes).map(function(code){
      return getOptionByCode(options, code);
    }).filter(Boolean);
  }

  function sortOptionsByOrder(list, order){
    return (order || []).map(function(code){
      return (list || []).find(function(item){
        return item.code === code;
      });
    }).filter(Boolean);
  }

  function ruleMatches(rule, text, domain, actions){
    var actionCodes = (actions || []).map(function(action){
      return action.code;
    });

    if(rule.domainCodes && rule.domainCodes.length && rule.domainCodes.indexOf(domain.code) === -1){
      return false;
    }

    if(rule.actionCodes && rule.actionCodes.length && !rule.actionCodes.some(function(code){
      return actionCodes.indexOf(code) > -1;
    })){
      return false;
    }

    if(rule.anyKeywords && rule.anyKeywords.length && !rule.anyKeywords.some(function(keyword){
      return text.indexOf(keyword) > -1;
    })){
      return false;
    }

    if(rule.allKeywords && rule.allKeywords.length && !rule.allKeywords.every(function(keyword){
      return text.indexOf(keyword) > -1;
    })){
      return false;
    }

    return true;
  }

  function inferPainOptions(text, domain, actions){
    var inferredCodes = [];

    PAIN_INFERENCE_RULES.forEach(function(rule){
      if(ruleMatches(rule, text, domain, actions)){
        inferredCodes.push(rule.painCode);
      }
    });

    return sortOptionsByOrder(mapCodesToOptions(inferredCodes, painOptions), PAIN_ORDER);
  }

  function decorateInsight(selection){
    var domain = getOptionByCode(domainOptions, selection.domainCode, 'general') || getOptionByCode(domainOptions, 'general', 'general');
    var pains = sortOptionsByOrder(mapCodesToOptions(selection.painCodes, painOptions), PAIN_ORDER);
    var actions = sortOptionsByOrder(mapCodesToOptions(selection.actionCodes, actionOptions), ACTION_ORDER);

    return {
      domainCode: domain.code,
      painCodes: pains.map(function(item){ return item.code; }),
      actionCodes: actions.map(function(item){ return item.code; }),
      domain: domain,
      pains: pains,
      actions: actions
    };
  }

  function buildThreeDimensionalInsight(input){
    var text = normalizeText(input);
    var domain = detectSingleByConfig(text, domainOptions, 'general');
    var actions = detectMultiByConfig(text, actionOptions);
    var directPains = detectMultiByConfig(text, painOptions);
    var inferredPains = inferPainOptions(text, domain, actions);
    var pains = sortOptionsByOrder(
      mapCodesToOptions(
        directPains.map(function(item){ return item.code; }).concat(
          inferredPains.map(function(item){ return item.code; })
        ),
        painOptions
      ),
      PAIN_ORDER
    );

    return decorateInsight({
      domainCode: domain.code,
      painCodes: pains.map(function(item){ return item.code; }),
      actionCodes: actions.map(function(item){ return item.code; })
    });
  }

  function buildThreeDimensionalInsightFromSelection(selection){
    return decorateInsight(selection || {});
  }

  function detectRequirementType(input){
    var text = normalizeText(input);
    var detected = requirementTypeOrder.find(function(type){
      var definition = getTypeDefinition(type);
      return (definition.keywords || []).some(function(keyword){
        return text.indexOf(keyword) > -1;
      });
    });

    return detected || defaultType;
  }

  function getRequirementTypeName(type){
    return getTypeDefinition(type).name || getTypeDefinition(defaultType).name;
  }

  function getQuestionsByType(type){
    var definition = getTypeDefinition(type);
    return (definition.questions || []).slice();
  }

  function getPainDisplay(pains){
    return (pains || []).length
      ? pains.map(function(item){ return item.name; }).join('、')
      : '待确认';
  }

  function getActionDisplay(actions){
    return (actions || []).length
      ? actions.map(function(item){ return item.name; }).join('、')
      : '待确认';
  }

  function buildActionGuessText(actions){
    var codes = (actions || []).map(function(item){
      return item.code;
    });

    if(codes.indexOf('auto_generate') > -1 && codes.indexOf('data_view') > -1){
      return '自动生成并展示关键数据';
    }

    if(codes.indexOf('auto_flow') > -1){
      return '自动流转流程节点';
    }

    if(codes.indexOf('auto_sync') > -1){
      return '自动同步关键数据';
    }

    if(codes.indexOf('auto_remind') > -1){
      return '自动提醒相关人员';
    }

    if(codes.indexOf('auto_control') > -1){
      return '自动控制关键节点';
    }

    if(codes.indexOf('auto_generate') > -1){
      return '自动生成关键结果';
    }

    if(codes.indexOf('data_view') > -1){
      return '展示关键数据';
    }

    return '支持关键处理动作';
  }

  function buildLeadText(type){
    switch(type){
      case 'report':
        return '你可能不只是想要一张报表';
      case 'reminder':
        return '你可能不只是想要一个提醒';
      case 'workflow':
        return '你可能不只是想把流程搬到线上';
      case 'integration':
        return '你可能不只是想做一个系统对接';
      case 'automation':
        return '你可能不只是想做一个自动化功能';
      case 'permission':
        return '你可能不只是想开一个权限';
      default:
        return '你可能不只是想要一个功能';
    }
  }

  function buildRealIntentGuess(type, insight){
    var domainName = insight.domain.name === '通用' ? '当前业务' : insight.domain.name;
    var painText = (insight.pains || []).length
      ? insight.pains.map(function(item){ return item.phrase || item.name; }).join('、')
      : '当前核心痛点';
    var actionText = buildActionGuessText(insight.actions);
    var tail = insight.domain.code === 'procurement'
      ? '提升采购执行效率。'
      : '让' + domainName + '场景处理得更及时、更准确、更省人工。';

    return buildLeadText(type) + '，而是希望解决' + domainName + '场景下' + painText + '的问题，通过系统' + actionText + '，' + tail;
  }

  function buildAiUnderstanding(type, insight){
    return '初步看，这是一个【' + getRequirementTypeName(type) + '】，更接近【' + insight.domain.name + '】场景，重点在【' + getPainDisplay(insight.pains) + '】。';
  }

  function buildGenericExampleAnswers(insight){
    var domainName = insight.domain.name === '通用' ? '相关业务' : insight.domain.name;
    var painText = (insight.pains || []).length
      ? insight.pains.map(function(item){ return item.name; }).join('、')
      : '慢、漏、错或人工重复';

    return {
      affected_users: domainName + '相关处理人员和负责人',
      pain_focus: painText,
      desired_step: buildActionGuessText(insight.actions)
    };
  }

  function buildClarifyPayloadByInsight(insight){
    var key = insight.domain.code === 'procurement' ? 'procurement' : 'general';
    var config = QUESTION_CONFIG[key] || QUESTION_CONFIG.general || { questions: [], exampleAnswers: {} };
    var exampleAnswers = key === 'procurement'
      ? Object.assign({}, config.exampleAnswers || {})
      : buildGenericExampleAnswers(insight);

    return {
      questions: (config.questions || []).map(function(question){
        return Object.assign({}, question);
      }),
      exampleAnswers: exampleAnswers
    };
  }

  function mockAiAnalyze(input){
    var type = detectRequirementType(input);
    var definition = getTypeDefinition(type);
    var threeDimInsight = buildThreeDimensionalInsight(input);
    var clarifyPayload = buildClarifyPayloadByInsight(threeDimInsight);

    return {
      type: type,
      typeName: definition.name,
      category: definition.name,
      newSentence: definition.previewSentence,
      detail: definition.previewDetail,
      aiUnderstanding: buildAiUnderstanding(type, threeDimInsight),
      realIntentGuess: buildRealIntentGuess(type, threeDimInsight),
      threeDimInsight: threeDimInsight,
      questions: clarifyPayload.questions,
      exampleAnswers: clarifyPayload.exampleAnswers
    };
  }

  function makePendingQuestions(questions, answers, insight){
    var missing = (questions || []).filter(function(question){
      return normalizeAnswer(answers[question.key]) === '待确认';
    }).map(function(question){
      return question.label;
    });

    if((insight.pains || []).length === 0){
      missing.push('痛点类型仍需确认');
    }

    if((insight.actions || []).length === 0){
      missing.push('系统动作仍需确认');
    }

    if(missing.length === 0){
      return '目前信息已基本够用，可以直接修改后提交。';
    }

    return '还需补充：' + missing.join('；');
  }

  function buildProcurementCard(analysis, answers, insight){
    var focus = normalizeAnswer(answers.procurement_focus);
    var audience = normalizeAnswer(answers.procurement_audience);
    var trigger = normalizeAnswer(answers.procurement_trigger);
    var actionPhrase = buildActionGuessText(insight.actions);

    return {
      refined_request: '希望在采购场景下，围绕' + focus + '，主要给' + audience + '使用，触发方式为' + trigger + '，由系统' + actionPhrase + '。',
      target_user: audience,
      system_action: getActionDisplay(insight.actions),
      input_data: focus,
      output_result: '围绕' + focus + '的结果输出。',
      delivery_method: trigger,
      success_metric: '采购执行和供应链负责人能更及时地拿到关键结果并做出响应。'
    };
  }

  function buildGeneralCard(analysis, answers, insight){
    var affectedUsers = normalizeAnswer(answers.affected_users);
    var painFocus = normalizeAnswer(answers.pain_focus);
    var desiredStep = normalizeAnswer(answers.desired_step);
    var domainName = insight.domain.name === '通用' ? '当前业务' : insight.domain.name;

    return {
      refined_request: '希望在' + domainName + '场景下，主要为' + affectedUsers + '解决“' + painFocus + '”的问题，并由系统完成“' + desiredStep + '”。',
      target_user: affectedUsers,
      system_action: getActionDisplay(insight.actions),
      input_data: painFocus,
      output_result: '系统完成“' + desiredStep + '”后的结果输出。',
      delivery_method: '待确认',
      success_metric: domainName + '场景下的处理效率和准确性得到改善。'
    };
  }

  function buildDemandCard(original, analysis, answers){
    var insight = analysis.threeDimInsight || buildThreeDimensionalInsight(original);
    var baseCard = insight.domain.code === 'procurement'
      ? buildProcurementCard(analysis, answers, insight)
      : buildGeneralCard(analysis, answers, insight);
    var painLabels = getPainDisplay(insight.pains);
    var actionLabels = getActionDisplay(insight.actions);
    var realIntentGuess = buildRealIntentGuess(analysis.type, insight);
    var domainName = insight.domain.name;

    return {
      requirement_type: analysis.typeName,
      requirement_type_code: analysis.type,
      original_request: original,
      ai_understanding: analysis.aiUnderstanding,
      core_goal: realIntentGuess,
      real_intent_guess: realIntentGuess,
      refined_request: baseCard.refined_request,
      pending_questions: makePendingQuestions(analysis.questions, answers, insight),
      pain_point: painLabels,
      target_user: baseCard.target_user,
      system_action: actionLabels,
      input_data: baseCard.input_data,
      output_result: baseCard.output_result,
      delivery_method: baseCard.delivery_method,
      success_metric: baseCard.success_metric,
      domain_name: domainName,
      pain_labels: painLabels,
      action_labels: actionLabels,
      three_dim_summary: '业务域：' + domainName + '｜痛点类型：' + painLabels + '｜系统动作：' + actionLabels
    };
  }

  function summarizeSentence(card){
    return normalizeAnswer(card.rewritten_request || card.refined_request);
  }

  function makeDetailText(card){
    var report = card.structured_report || {};
    return '建议提交版本：' + normalizeAnswer(card.refined_request || card.rewritten_request) + ' 真实诉求：' + normalizeAnswer(card.real_intent_guess) + ' 仍需确认：' + normalizeAnswer(card.pending_questions || report.input);
  }

  function uniqueTextList(values){
    return (values || []).filter(function(value, index, list){
      return value && list.indexOf(value) === index;
    });
  }

  function appendMissingText(text, label, values){
    var base = normalizeAnswer(text);
    var missing = uniqueTextList(values || []).filter(function(value){
      return base.indexOf(value) === -1;
    });

    if(!missing.length){
      return base;
    }

    return base.replace(/[。；;\s]*$/, '') + '；' + label + '：' + missing.join('、') + '。';
  }

  function selectionPhrase(values, fallback){
    var cleaned = uniqueTextList(values || []);
    if(!cleaned.length) return fallback || '';
    if(cleaned.length === 1) return cleaned[0];
    return cleaned.slice(0, -1).join('、') + '和' + cleaned[cleaned.length - 1];
  }

  function getQuickSelectionOptionsByDomainCode(domainCode){
    var library = app.quickSelectionLibrary || {};
    var source = library[domainCode] || library.general || {};

    return {
      affected_roles: (source.affected_roles || []).slice(),
      focus_points: (source.focus_points || []).slice(),
      system_expectations: (source.system_expectations || []).slice()
    };
  }

  function buildUncertainItemsForInsight(insight){
    var actionMap = {
      data_view: ['数据来源', '关键字段', '查看方式'],
      auto_remind: ['提醒对象', '提醒时点', '触发规则'],
      auto_flow: ['发起角色', '审批节点', '异常处理规则'],
      auto_sync: ['主数据来源', '同步频率', '失败处理方式'],
      auto_generate: ['生成口径', '输出频率', '发送方式'],
      auto_control: ['拦截规则', '例外放行机制', '责任人']
    };
    var domainMap = {
      procurement: ['BOM/库存数据口径', '使用对象', '触发频率'],
      finance: ['差异判断口径', '数据源系统', '输出对象'],
      hr: ['责任分工', '通知对象', '节点顺序'],
      legal: ['提醒对象', '提前天数', '升级规则'],
      warehouse: ['库存口径', '异常阈值', '同步时效'],
      production: ['触发条件', '责任岗位', '异常闭环'],
      sales: ['跟进对象', '提醒时机', '输出结果'],
      general: ['影响对象', '触发条件', '成功标准']
    };
    var items = [];

    (insight.actions || []).forEach(function(action){
      items = items.concat(actionMap[action.code] || []);
    });

    items = items.concat(domainMap[insight.domain.code] || domainMap.general);
    return uniqueTextList(items).slice(0, 3);
  }

  function buildSuggestedRequestFromInsight(input, type, insight){
    var domainName = insight.domain.name === '通用' ? '当前业务' : insight.domain.name;
    var users = (app.getQuickSelectionOptionsByDomainCode(insight.domain.code).affected_roles || []).slice(0, 2);
    var painText = getPainDisplay(insight.pains);
    var actionText = buildActionGuessText(insight.actions);

    return '希望系统在' + domainName + '场景下，帮助' + (users.length ? users.join('、') : '相关人员') + actionText + '，处理' + painText + '相关问题，并形成可跟进的结果。';
  }

  function buildFallbackDiagnosis(input, insight, targetUsers){
    var painText = getPainDisplay(insight.pains);
    var actionText = buildActionGuessText(insight.actions);
    var domainName = insight.domain.name === '通用' ? '待业务确认' : insight.domain.name;
    var manualActions = input.indexOf('人工') > -1 || input.indexOf('手工') > -1
      ? ['人工处理或跟进']
      : [];
    var breakpoint = manualActions.length
      ? '关键处理动作依赖人工完成，缺少系统化触发、提醒或闭环。'
      : '流程断点尚不明确，需要确认当前卡在哪个节点或责任角色。';

    return {
      explicit_facts: [input ? '原话表达：' + input : '原话未提供足够信息'],
      inferred_context: ['基于本地词典判断，业务域候选为' + domainName + '。'],
      business_domain_candidates: [{ name: domainName, confidence: domainName === '待业务确认' ? 0.35 : 0.62, reason: '本地关键词匹配，仅作兜底参考' }],
      related_system_candidates: [],
      target_users: targetUsers,
      current_process: manualActions.length ? '当前看起来依赖人工处理或跟进。' : '当前处理方式待业务确认。',
      manual_actions: manualActions,
      process_breakpoint: breakpoint,
      pain_root_cause: painText === '待确认' ? '待业务确认' : '当前痛点集中在' + painText + '，具体根因仍需确认。',
      business_impact: '可能影响' + domainName + '场景下的响应及时性、责任闭环和业务判断。',
      desired_system_behavior: [actionText],
      uncertain_items: ['触发条件需要确认', '数据来源需要确认', '责任角色需要确认']
    };
  }

  function buildFallbackStructuredReport(insight, suggestedRequest, selectedOptions){
    var domainCode = insight.domain.code;
    var selected = selectedOptions || {};
    var roles = uniqueTextList(selected.affected_roles || []);
    var focusPoints = uniqueTextList(selected.focus_points || []);
    var expectations = uniqueTextList(selected.system_expectations || []);
    var rolesMap = {
      procurement: '采购团队主导，采购执行与供应链负责人使用',
      finance: '财务团队主导，财务专员和负责人使用',
      hr: 'HR 主导，HR、IT 支持和用人部门协同使用',
      legal: '法务主导，法务与业务负责人协同使用',
      warehouse: '仓储团队主导，仓库管理员和计划人员使用',
      production: '生产计划团队主导，计划人员和车间主管使用',
      sales: '销售团队主导，销售执行和负责人使用',
      general: '待业务确认'
    };
    var whereMap = {
      procurement: '采购执行 / 供应链协同场景',
      finance: '财务对账 / 月结处理场景',
      hr: '员工入职协同场景',
      legal: '合同管理 / 到期跟进场景',
      warehouse: '仓储库存管理 / 下单前库存校验场景',
      production: '生产工单跟踪 / 计划协同场景',
      sales: '客户跟进 / 订单推进场景',
      general: '当前业务处理场景'
    };
    var whatMap = {
      procurement: '采购/供应影响识别与结果推送',
      finance: '多系统对账差异自动汇总',
      hr: '入职账号、设备与权限协同',
      legal: '合同到期提醒与跟进',
      warehouse: '库存账实差异自动比对与缺货提醒',
      production: '工单进度透明化与异常提醒',
      sales: '客户跟进与订单进度提醒',
      general: '关键数据与待处理动作自动跟进'
    };

    var report = {
      why: (insight.pains || []).length ? '当前重点痛点是' + insight.pains.map(function(item){ return item.name; }).join('、') + '。' : '待业务确认',
      what: whatMap[domainCode] || '待业务确认',
      where: whereMap[domainCode] || '待业务确认',
      who: rolesMap[domainCode] || '待业务确认',
      input: '待业务确认',
      output: suggestedRequest || '待业务确认',
      how: ['先确认数据来源和规则。', '由系统自动处理关键动作。', '将结果推送给相关人员跟进。'],
      monitor: ['处理时效提升', '人工重复工作下降'],
      howmuch: '建议先按一个重点场景试点推进，具体投入待业务和 IT 确认。'
    };

    if(roles.length){
      report.who = selectionPhrase(roles);
    }
    if(focusPoints.length){
      report.why = '当前优先解决' + selectionPhrase(focusPoints) + '带来的业务影响。';
      report.what = '处理' + selectionPhrase(focusPoints);
      report.input = '围绕' + selectionPhrase(focusPoints) + '触发分析或提醒';
      report.output = selectionPhrase(focusPoints) + '的处理结果和闭环状态';
    }
    if(expectations.length){
      report.what = '通过' + selectionPhrase(expectations) + (focusPoints.length ? '处理' + selectionPhrase(focusPoints) : '支撑业务处理');
      report.output = '形成' + selectionPhrase(expectations) + '后的处理结果';
    }
    if(focusPoints.length || expectations.length || roles.length){
      report.how.splice(1, 0, '系统围绕' + selectionPhrase(focusPoints, '关键风险') + selectionPhrase(expectations, '完成处理') + '，并推送给' + selectionPhrase(roles, '相关人员') + '跟进。');
      report.how = report.how.slice(0, 4);
    }

    return report;
  }

  function createFallbackApiAnalysis(input){
    var base = mockAiAnalyze(input);
    var insight = base.threeDimInsight;
    var suggested = buildSuggestedRequestFromInsight(input, base.type, insight);
    var targetUsers = (app.getQuickSelectionOptionsByDomainCode(insight.domain.code).affected_roles || []).slice(0, 2);
    var diagnosis = buildFallbackDiagnosis(input, insight, targetUsers);
    var businessObject = (diagnosis.explicit_facts || []).join(' ').match(/(质量异常|整改任务|生产工单|采购订单|供应商交期|物料|库存|服务单|维修单|客户订单|权限申请)/);
    businessObject = businessObject ? businessObject[1] : (insight.domain.name === '通用' ? '待确认业务对象' : insight.domain.name + '对象');

    diagnosis.business_object = diagnosis.business_object || businessObject;
    diagnosis.current_manual_process = diagnosis.current_manual_process || diagnosis.current_process;
    diagnosis.passive_consequence = diagnosis.passive_consequence || diagnosis.business_impact;
    diagnosis.minimum_system_behavior = diagnosis.minimum_system_behavior || diagnosis.desired_system_behavior;

    return {
      original_request: input,
      diagnosis: diagnosis,
      rewritten_request: suggested,
      business_domain: insight.domain.name,
      business_object: businessObject,
      related_systems: [],
      pain_points: (insight.pains || []).map(function(item){ return item.name; }),
      system_actions: (insight.actions || []).map(function(item){ return item.name; }),
      target_users: targetUsers,
      current_manual_process: diagnosis.current_manual_process,
      process_breakpoint: diagnosis.process_breakpoint,
      passive_consequence: diagnosis.passive_consequence,
      minimum_system_behavior: diagnosis.minimum_system_behavior,
      real_intent: base.realIntentGuess,
      suggested_request: suggested,
      confirmation_options: getQuickSelectionOptionsByDomainCode(insight.domain.code),
      scenario_form: null,
      uncertain_items: buildUncertainItemsForInsight(insight),
      structured_report: buildFallbackStructuredReport(insight, suggested),
      mode: 'local-fallback'
    };
  }

  function createFallbackRefineResult(userInput, analysisResult, selectedOptions){
    var roles = uniqueTextList((selectedOptions && selectedOptions.affected_roles) || []);
    var focusPoints = uniqueTextList((selectedOptions && selectedOptions.focus_points) || []);
    var expectations = uniqueTextList((selectedOptions && selectedOptions.system_expectations) || []);
    var domainName = (analysisResult && analysisResult.business_domain) || '通用';
    var painPoints = uniqueTextList((analysisResult && analysisResult.pain_points) || []);
    var uncertainItems = [];
    var sentence = '希望系统在' + domainName + '场景下帮助' + selectionPhrase(roles, '相关人员') +
      '通过' + selectionPhrase(expectations, '自动处理') +
      '及时处理' + selectionPhrase(focusPoints, painPoints.length ? painPoints.slice(0, 2).join('、') : '核心痛点') +
      '，减少人工追问和风险遗漏。';

    if(!roles.length){
      uncertainItems.push('影响对象');
    }
    if(!focusPoints.length){
      uncertainItems.push('关注重点');
    }
    if(!expectations.length){
      uncertainItems.push('系统期望动作');
    }

    uncertainItems = uniqueTextList(uncertainItems.concat((analysisResult && analysisResult.uncertain_items) || [])).slice(0, 3);

    return {
      refined_request: sentence,
      rewritten_request: sentence,
      target_users: roles.length ? roles : ((analysisResult && analysisResult.target_users) || []),
      uncertain_items: uncertainItems,
      structured_report: buildFallbackStructuredReport(app.buildThreeDimensionalInsight(userInput), sentence, selectedOptions),
      mode: 'local-fallback'
    };
  }

  app.getTypeDefinition = getTypeDefinition;
  app.getRequirementTypeName = getRequirementTypeName;
  app.getQuestionsByType = getQuestionsByType;
  app.getDomainOptions = function(){ return domainOptions.slice(); };
  app.getPainOptions = function(){ return painOptions.slice(); };
  app.getActionOptions = function(){ return actionOptions.slice(); };
  app.detectRequirementType = detectRequirementType;
  app.buildThreeDimensionalInsight = buildThreeDimensionalInsight;
  app.buildThreeDimensionalInsightFromSelection = buildThreeDimensionalInsightFromSelection;
  app.buildClarifyPayloadByInsight = buildClarifyPayloadByInsight;
  app.buildRealIntentGuess = buildRealIntentGuess;
  app.buildAiUnderstanding = buildAiUnderstanding;
  app.mockAiAnalyze = mockAiAnalyze;
  app.buildDemandCard = buildDemandCard;
  app.summarizeSentence = summarizeSentence;
  app.makeDetailText = makeDetailText;
  app.getQuickSelectionOptionsByDomainCode = getQuickSelectionOptionsByDomainCode;
  app.buildUncertainItemsForInsight = buildUncertainItemsForInsight;
  app.createFallbackApiAnalysis = createFallbackApiAnalysis;
  app.createFallbackRefineResult = createFallbackRefineResult;
})(window);
