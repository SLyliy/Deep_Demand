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
    return text || '???';
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
      ? pains.map(function(item){ return item.name; }).join('?')
      : '???';
  }

  function getActionDisplay(actions){
    return (actions || []).length
      ? actions.map(function(item){ return item.name; }).join('?')
      : '???';
  }

  function buildActionGuessText(actions){
    var codes = (actions || []).map(function(item){
      return item.code;
    });

    if(codes.indexOf('auto_generate') > -1 && codes.indexOf('data_view') > -1){
      return '???????????';
    }

    if(codes.indexOf('auto_flow') > -1){
      return '????????';
    }

    if(codes.indexOf('auto_sync') > -1){
      return '????????';
    }

    if(codes.indexOf('auto_remind') > -1){
      return '????????';
    }

    if(codes.indexOf('auto_control') > -1){
      return '????????';
    }

    if(codes.indexOf('auto_generate') > -1){
      return '????????';
    }

    if(codes.indexOf('data_view') > -1){
      return '??????';
    }

    return '????????';
  }

  function buildLeadText(type){
    switch(type){
      case 'report':
        return '????????????';
      case 'reminder':
        return '????????????';
      case 'workflow':
        return '??????????????';
      case 'integration':
        return '??????????????';
      case 'automation':
        return '???????????????';
      case 'permission':
        return '????????????';
      default:
        return '????????????';
    }
  }

  function buildRealIntentGuess(type, insight){
    var domainName = insight.domain.name === '??' ? '????' : insight.domain.name;
    var painText = (insight.pains || []).length
      ? insight.pains.map(function(item){ return item.phrase || item.name; }).join('?')
      : '??????';
    var actionText = buildActionGuessText(insight.actions);
    var tail = insight.domain.code === 'procurement'
      ? '?????????'
      : '?' + domainName + '??????????????????';

    return buildLeadText(type) + '???????' + domainName + '???' + painText + '????????' + actionText + '?' + tail;
  }

  function buildAiUnderstanding(type, insight){
    return '?????????' + getRequirementTypeName(type) + '??????' + insight.domain.name + '????????' + getPainDisplay(insight.pains) + '??';
  }

  function buildGenericExampleAnswers(insight){
    var domainName = insight.domain.name === '??' ? '????' : insight.domain.name;
    var painText = (insight.pains || []).length
      ? insight.pains.map(function(item){ return item.name; }).join('?')
      : '??????????';

    return {
      affected_users: domainName + '??????????',
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
      return normalizeAnswer(answers[question.key]) === '???';
    }).map(function(question){
      return question.label;
    });

    if((insight.pains || []).length === 0){
      missing.push('????????');
    }

    if((insight.actions || []).length === 0){
      missing.push('????????');
    }

    if(missing.length === 0){
      return '????????????????????';
    }

    return '?????' + missing.join('?');
  }

  function buildProcurementCard(analysis, answers, insight){
    var focus = normalizeAnswer(answers.procurement_focus);
    var audience = normalizeAnswer(answers.procurement_audience);
    var trigger = normalizeAnswer(answers.procurement_trigger);
    var actionPhrase = buildActionGuessText(insight.actions);

    return {
      refined_request: '???????????' + focus + '????' + audience + '????????' + trigger + '????' + actionPhrase + '?',
      target_user: audience,
      system_action: getActionDisplay(insight.actions),
      input_data: focus,
      output_result: '??' + focus + '??????',
      delivery_method: trigger,
      success_metric: '????????????????????????????'
    };
  }

  function buildGeneralCard(analysis, answers, insight){
    var affectedUsers = normalizeAnswer(answers.affected_users);
    var painFocus = normalizeAnswer(answers.pain_focus);
    var desiredStep = normalizeAnswer(answers.desired_step);
    var domainName = insight.domain.name === '??' ? '????' : insight.domain.name;

    return {
      refined_request: '???' + domainName + '???????' + affectedUsers + '???' + painFocus + '????????????' + desiredStep + '??',
      target_user: affectedUsers,
      system_action: getActionDisplay(insight.actions),
      input_data: painFocus,
      output_result: '?????' + desiredStep + '????????',
      delivery_method: '???',
      success_metric: domainName + '?????????????????'
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
      three_dim_summary: '????' + domainName + '??????' + painLabels + '??????' + actionLabels
    };
  }

  function summarizeSentence(card){
    return normalizeAnswer(card.rewritten_request || card.refined_request);
  }

  function makeDetailText(card){
    var report = card.structured_report || {};
    return '???????' + normalizeAnswer(card.refined_request || card.rewritten_request) + ' ?????' + normalizeAnswer(card.real_intent_guess) + ' ?????' + normalizeAnswer(card.pending_questions || report.input);
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

    return base.replace(/[??;\s]*$/, '') + '?' + label + '?' + missing.join('?') + '?';
  }

  function selectionPhrase(values, fallback){
    var cleaned = uniqueTextList(values || []);
    if(!cleaned.length) return fallback || '';
    if(cleaned.length === 1) return cleaned[0];
    return cleaned.slice(0, -1).join('?') + '?' + cleaned[cleaned.length - 1];
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
      data_view: ['????', '????', '????'],
      auto_remind: ['????', '????', '????'],
      auto_flow: ['????', '????', '??????'],
      auto_sync: ['?????', '????', '??????'],
      auto_generate: ['????', '????', '????'],
      auto_control: ['????', '??????', '???']
    };
    var domainMap = {
      procurement: ['BOM/??????', '????', '????'],
      finance: ['??????', '?????', '????'],
      hr: ['????', '????', '????'],
      legal: ['????', '????', '????'],
      warehouse: ['????', '????', '????'],
      production: ['????', '????', '????'],
      sales: ['????', '????', '????'],
      general: ['????', '????', '????']
    };
    var items = [];

    (insight.actions || []).forEach(function(action){
      items = items.concat(actionMap[action.code] || []);
    });

    items = items.concat(domainMap[insight.domain.code] || domainMap.general);
    return uniqueTextList(items).slice(0, 3);
  }

  function buildSuggestedRequestFromInsight(input, type, insight){
    var domainName = insight.domain.name === '??' ? '????' : insight.domain.name;
    var users = (app.getQuickSelectionOptionsByDomainCode(insight.domain.code).affected_roles || []).slice(0, 2);
    var painText = getPainDisplay(insight.pains);
    var actionText = buildActionGuessText(insight.actions);

    return '?????' + domainName + '??????' + (users.length ? users.join('?') : '????') + actionText + '???' + painText + '???????????????';
  }

  function buildFallbackDiagnosis(input, insight, targetUsers){
    var painText = getPainDisplay(insight.pains);
    var actionText = buildActionGuessText(insight.actions);
    var domainName = insight.domain.name === '??' ? '?????' : insight.domain.name;
    var manualActions = input.indexOf('??') > -1 || input.indexOf('??') > -1
      ? ['???????']
      : [];
    var breakpoint = manualActions.length
      ? '???????????????????????????'
      : '???????????????????????????';

    return {
      explicit_facts: [input ? '?????' + input : '?????????'],
      inferred_context: ['???????????????' + domainName + '?'],
      business_domain_candidates: [{ name: domainName, confidence: domainName === '?????' ? 0.35 : 0.62, reason: '??????????????' }],
      related_system_candidates: [],
      target_users: targetUsers,
      current_process: manualActions.length ? '???????????????' : '????????????',
      manual_actions: manualActions,
      process_breakpoint: breakpoint,
      pain_root_cause: painText === '???' ? '?????' : '???????' + painText + '??????????',
      business_impact: '????' + domainName + '????????????????????',
      desired_system_behavior: [actionText],
      uncertain_items: ['????????', '????????', '????????']
    };
  }

  function buildFallbackStructuredReport(insight, suggestedRequest, selectedOptions){
    var domainCode = insight.domain.code;
    var selected = selectedOptions || {};
    var roles = uniqueTextList(selected.affected_roles || []);
    var focusPoints = uniqueTextList(selected.focus_points || []);
    var expectations = uniqueTextList(selected.system_expectations || []);
    var rolesMap = {
      procurement: '????????????????????',
      finance: '?????????????????',
      hr: 'HR ???HR?IT ???????????',
      legal: '?????????????????',
      warehouse: '???????????????????',
      production: '????????????????????',
      sales: '?????????????????',
      general: '?????'
    };
    var whereMap = {
      procurement: '???? / ???????',
      finance: '???? / ??????',
      hr: '????????',
      legal: '???? / ??????',
      warehouse: '?????? / ?????????',
      production: '?????? / ??????',
      sales: '???? / ??????',
      general: '????????'
    };
    var whatMap = {
      procurement: '??/???????????',
      finance: '???????????',
      hr: '????????????',
      legal: '?????????',
      warehouse: '???????????????',
      production: '????????????',
      sales: '???????????',
      general: '??????????????'
    };

    var report = {
      why: (insight.pains || []).length ? '???????' + insight.pains.map(function(item){ return item.name; }).join('?') + '?' : '?????',
      what: whatMap[domainCode] || '?????',
      where: whereMap[domainCode] || '?????',
      who: rolesMap[domainCode] || '?????',
      input: '?????',
      output: suggestedRequest || '?????',
      how: ['???????????', '????????????', '?????????????'],
      monitor: ['??????', '????????'],
      howmuch: '??????????????????????? IT ???'
    };

    if(roles.length){
      report.who = selectionPhrase(roles);
    }
    if(focusPoints.length){
      report.why = '??????' + selectionPhrase(focusPoints) + '????????';
      report.what = '??' + selectionPhrase(focusPoints);
      report.input = '??' + selectionPhrase(focusPoints) + '???????';
      report.output = selectionPhrase(focusPoints) + '??????????';
    }
    if(expectations.length){
      report.what = '??' + selectionPhrase(expectations) + (focusPoints.length ? '??' + selectionPhrase(focusPoints) : '??????');
      report.output = '??' + selectionPhrase(expectations) + '??????';
    }
    if(focusPoints.length || expectations.length || roles.length){
      report.how.splice(1, 0, '????' + selectionPhrase(focusPoints, '????') + selectionPhrase(expectations, '????') + '?????' + selectionPhrase(roles, '????') + '???');
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
    var businessObject = (diagnosis.explicit_facts || []).join(' ').match(/(????|????|????|????|?????|??|??|???|???|????|????)/);
    businessObject = businessObject ? businessObject[1] : (insight.domain.name === '??' ? '???????' : insight.domain.name + '??');

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
    var domainName = (analysisResult && analysisResult.business_domain) || '??';
    var painPoints = uniqueTextList((analysisResult && analysisResult.pain_points) || []);
    var uncertainItems = [];
    var sentence = '?????' + domainName + '?????' + selectionPhrase(roles, '????') +
      '??' + selectionPhrase(expectations, '????') +
      '????' + selectionPhrase(focusPoints, painPoints.length ? painPoints.slice(0, 2).join('?') : '????') +
      '?????????????';

    if(!roles.length){
      uncertainItems.push('????');
    }
    if(!focusPoints.length){
      uncertainItems.push('????');
    }
    if(!expectations.length){
      uncertainItems.push('??????');
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
