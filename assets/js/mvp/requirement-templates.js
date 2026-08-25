(function(global){
  var app = global.DeepDemandMvp = global.DeepDemandMvp || {};

  app.defaultRequirementType = 'general';
  app.requirementTypeOrder = [
    'report',
    'reminder',
    'workflow',
    'permission',
    'integration',
    'automation',
    'general'
  ];

  app.DOMAIN_ORDER = [
    'procurement',
    'finance',
    'hr',
    'legal',
    'warehouse',
    'production',
    'sales',
    'general'
  ];

  app.DOMAIN_CONFIG = {
    procurement: {
      name: '采购',
      keywords: ['采购', '供应商', '请购', '交期', '到货', '缺料', 'BOM', '物料'],
      description: '采购执行、供应商协同、交付跟进相关场景'
    },
    finance: {
      name: '财务',
      keywords: ['财务', '对账', '关账', '凭证', '预算', '回款', '应收', '应付'],
      description: '财务核算、对账、预算和回款相关场景'
    },
    hr: {
      name: 'HR',
      keywords: ['HR', '人力', '员工', '入职', '转正', '离职', '考勤', '招聘', '编制'],
      description: '员工生命周期和人力流程相关场景'
    },
    legal: {
      name: '法务',
      keywords: ['法务', '合同', '盖章', '协议', '审查', '归档', '合规', '到期'],
      description: '合同、法务审批和合规管理相关场景'
    },
    warehouse: {
      name: '仓储',
      keywords: ['仓库', '仓储', '库存', '出入库', '库位', '盘点', '批次', '呆滞'],
      description: '库存、仓储执行和物流现场相关场景'
    },
    production: {
      name: '生产',
      keywords: ['生产', '制造', '工单', '排产', '车间', '产线', '设备', '工艺'],
      description: '生产制造、计划排程和车间执行相关场景'
    },
    sales: {
      name: '销售',
      keywords: ['销售', '客户', '商机', '报价', '订单', '线索', '回访', '签约'],
      description: '客户跟进、商机推进和销售管理相关场景'
    },
    general: {
      name: '通用',
      keywords: [],
      description: '尚未明确业务域的通用场景'
    }
  };

  app.PAIN_ORDER = [
    'timeliness',
    'omission',
    'accuracy',
    'manual_heavy',
    'workflow_block',
    'risk_hidden'
  ];

  app.PAIN_CONFIG = {
    timeliness: {
      name: '时效慢',
      keywords: ['慢', '太慢', '滞后', '不及时', '耗时', '周期长', '等待'],
      description: '处理速度慢、响应不及时',
      phrase: '响应不及时'
    },
    omission: {
      name: '容易漏',
      keywords: ['漏', '遗漏', '忘记', '漏掉', '漏发', '漏批', '漏处理'],
      description: '依赖人工记忆，容易遗漏',
      phrase: '容易遗漏'
    },
    accuracy: {
      name: '数据不准',
      keywords: ['不准', '错误', '偏差', '对不上', '差异', '口径不一致', '不一致'],
      description: '数据质量或口径存在偏差',
      phrase: '数据不够准确'
    },
    manual_heavy: {
      name: '人工太重',
      keywords: ['人工', '手工', '手动', '重复', 'excel', '表格', '复制粘贴', '人工计算'],
      description: '依赖大量人工重复处理',
      phrase: '人工处理工作重'
    },
    workflow_block: {
      name: '流程卡点',
      keywords: ['卡点', '卡住', '堵点', '退回', '审批慢', '流转慢', '卡在'],
      description: '流程推进存在明显卡点',
      phrase: '流程卡点明显'
    },
    risk_hidden: {
      name: '风险不可见',
      keywords: ['风险', '异常', '预警', '超期', '到期', '合规', '看不见', '不透明'],
      description: '关键风险不透明，难以及时发现',
      phrase: '风险不够可见'
    }
  };

  app.ACTION_ORDER = [
    'data_view',
    'auto_remind',
    'auto_flow',
    'auto_sync',
    'auto_generate',
    'auto_control'
  ];

  app.ACTION_CONFIG = {
    data_view: {
      name: '看数据',
      keywords: ['报表', '统计', '看板', '查看', '分析', '数据', '进度'],
      description: '查看、展示和分析关键数据',
      guessText: '展示关键数据'
    },
    auto_remind: {
      name: '自动提醒',
      keywords: ['提醒', '通知', '预警', '催办'],
      description: '自动通知相关人员',
      guessText: '自动提醒相关人员'
    },
    auto_flow: {
      name: '自动流转',
      keywords: ['审批', '流程', '流转', '加签', '退回', '入职', '开账号', '办权限', '发设备'],
      description: '自动推进流程节点',
      guessText: '自动流转流程节点'
    },
    auto_sync: {
      name: '自动同步',
      keywords: ['同步', '对接', '接口', '打通'],
      description: '自动同步多个系统的数据',
      guessText: '自动同步关键数据'
    },
    auto_generate: {
      name: '自动生成',
      keywords: ['生成', '汇总', '计算', '输出', '出报表'],
      description: '自动生成报表、结果或处理输出',
      guessText: '自动生成结果'
    },
    auto_control: {
      name: '自动控制',
      keywords: ['控制', '校验', '拦截', '限制', '锁定'],
      description: '自动校验、控制和拦截关键动作',
      guessText: '自动控制关键节点'
    }
  };

  app.PAIN_INFERENCE_RULES = [
    {
      painCode: 'manual_heavy',
      anyKeywords: ['自动计算', '自动汇总', '报表', '汇总', '同步'],
      actionCodes: ['auto_generate', 'auto_sync'],
      description: '当用户提到自动生成、汇总或同步时，通常隐含人工处理过重'
    },
    {
      painCode: 'timeliness',
      domainCodes: ['procurement'],
      anyKeywords: ['报表', 'BOM', '库存', '交期', '缺料'],
      description: '采购场景对交付时效和数据更新时效通常更敏感'
    },
    {
      painCode: 'omission',
      actionCodes: ['auto_remind'],
      anyKeywords: ['提醒', '通知', '到期'],
      description: '提醒类需求通常是为了解决遗漏问题'
    },
    {
      painCode: 'risk_hidden',
      anyKeywords: ['到期', '预警', '风险', '异常'],
      actionCodes: ['auto_remind', 'auto_control'],
      description: '到期、异常、预警类需求通常隐含风险不可见'
    },
    {
      painCode: 'workflow_block',
      actionCodes: ['auto_flow'],
      anyKeywords: ['审批', '流程', '流转', '入职', '开账号', '办权限', '发设备'],
      description: '流程类需求通常是要解决流程卡点'
    },
    {
      painCode: 'accuracy',
      anyKeywords: ['对账', '差异', '库存', '校验', '不准'],
      actionCodes: ['auto_sync', 'auto_control'],
      description: '同步、对账和校验类需求通常会指向数据准确性问题'
    }
  ];

  app.THREE_DIMENSION_QUESTION_CONFIG = {
    general: {
      questions: [
        { key: 'affected_users', label: '这件事主要影响谁？', placeholder: '例如：财务专员、仓库主管、销售经理' },
        { key: 'pain_focus', label: '现在最痛的是慢、漏、错，还是人工重复？', placeholder: '例如：对账太慢、总是漏跟进、人工汇总太多' },
        { key: 'desired_step', label: '你最希望系统替你完成哪一步？', placeholder: '例如：自动汇总差异、自动提醒负责人、自动流转审批' }
      ],
      exampleAnswers: {
        affected_users: '相关业务处理人员和负责人',
        pain_focus: '处理慢，人工重复多，还容易遗漏',
        desired_step: '自动汇总关键数据并推动后续处理'
      }
    },
    procurement: {
      questions: [
        { key: 'procurement_focus', label: '你最想关注的是缺料、交期、供应商响应，还是 BOM/库存数据？', placeholder: '例如：BOM/库存数据和缺料风险' },
        { key: 'procurement_audience', label: '结果主要给采购执行看，还是给供应链负责人看？', placeholder: '例如：采购执行和供应链负责人都要看' },
        { key: 'procurement_trigger', label: '是定时生成，还是异常或数据变化时触发？', placeholder: '例如：每天定时生成，异常时补发' }
      ],
      exampleAnswers: {
        procurement_focus: 'BOM/库存数据和缺料风险',
        procurement_audience: '采购执行人员和供应链负责人',
        procurement_trigger: '每天定时生成，异常或数据变化时补发'
      }
    }
  };

  app.quickSelectionLibrary = {
    procurement: {
      affected_roles: ['采购执行', '供应链负责人', '计划人员', '跨部门协作人员', '供应商'],
      focus_points: ['BOM/用量计算', '缺料风险', '交期响应', '供应商协同', '人工统计太重'],
      system_expectations: ['展示关键数据', '自动提醒', '自动同步', '自动生成结果', '自动拦截风险']
    },
    finance: {
      affected_roles: ['财务专员', '财务负责人', '业务部门', '跨部门协作人员', '管理层'],
      focus_points: ['月底对账', '差异汇总', '多系统取数', '人工比对太重', '口径不一致'],
      system_expectations: ['展示关键数据', '自动同步', '自动生成结果', '自动提醒', '自动拦截风险']
    },
    hr: {
      affected_roles: ['HR专员', '用人部门', 'IT支持', '跨部门协作人员', '新员工'],
      focus_points: ['入职步骤漏项', '账号开通', '设备发放', '权限办理', '流程协同慢'],
      system_expectations: ['自动流转', '自动提醒', '自动生成结果', '自动控制', '展示关键数据']
    },
    legal: {
      affected_roles: ['法务专员', '业务负责人', '部门负责人', '管理层', '客户/供应商'],
      focus_points: ['合同到期', '审批超时', '提醒对象不清', '合规风险', '归档缺失'],
      system_expectations: ['自动提醒', '自动流转', '展示关键数据', '自动控制', '自动生成结果']
    },
    warehouse: {
      affected_roles: ['仓库管理员', '计划人员', '采购执行', '跨部门协作人员', '管理层'],
      focus_points: ['库存不准', '缺货风险', '人工核对太重', '业务下单受影响', '异常库存发现太晚'],
      system_expectations: ['展示关键数据', '自动同步', '自动提醒', '自动生成结果', '自动拦截风险']
    },
    production: {
      affected_roles: ['生产计划员', '车间主管', '设备人员', '跨部门协作人员', '管理层'],
      focus_points: ['排产不及时', '工单流转', '设备异常', '人工跟单', '异常反馈滞后'],
      system_expectations: ['自动流转', '自动提醒', '展示关键数据', '自动同步', '自动控制']
    },
    sales: {
      affected_roles: ['销售执行', '销售负责人', '客户', '跨部门协作人员', '管理层'],
      focus_points: ['客户跟进', '商机推进', '报价反馈', '订单协同', '数据分散'],
      system_expectations: ['展示关键数据', '自动提醒', '自动流转', '自动生成结果', '自动同步']
    },
    general: {
      affected_roles: ['一线执行人员', '部门负责人', '管理层', '跨部门协作人员', '客户/供应商'],
      focus_points: ['太慢', '容易漏', '数据不准', '人工重复', '流程卡住'],
      system_expectations: ['展示关键数据', '自动提醒', '自动流转', '自动同步', '自动生成结果']
    }
  };

  app.requirementTypes = {
    report: {
      code: 'report',
      name: '报表类需求',
      keywords: ['报表', '统计', '导出', '看板'],
      previewSentence: '自动生成并推送业务报表，减少人工汇总和转发',
      previewDetail: '你可能真正想要的，不只是“做一张报表”，而是让关键数据自动整理并按时送到使用人手里。'
    },
    reminder: {
      code: 'reminder',
      name: '提醒/预警类需求',
      keywords: ['提醒', '通知', '预警', '到期'],
      previewSentence: '自动提醒关键事项，避免人工记忆和漏处理',
      previewDetail: '你可能真正想要的，不是“收到一条消息”，而是把容易忘、容易漏的事情交给系统盯住。'
    },
    workflow: {
      code: 'workflow',
      name: '流程审批类需求',
      keywords: ['审批', '流程', '流转', '节点'],
      previewSentence: '把线下流程搬到系统里，减少卡点和漏批',
      previewDetail: '你可能真正想要的，不是“加个审批按钮”，而是让流程可追踪、少卡住、少漏掉。'
    },
    permission: {
      code: 'permission',
      name: '权限类需求',
      keywords: ['权限', '账号', '角色', '访问'],
      previewSentence: '把权限申请边界说清楚，避免反复沟通',
      previewDetail: '你可能真正想要的，不只是“开个权限”，而是明确谁能看什么、谁来批、多久有效。'
    },
    integration: {
      code: 'integration',
      name: '系统集成/数据同步类需求',
      keywords: ['同步', '对接', '接口', '打通'],
      previewSentence: '打通系统并自动同步数据，减少重复录入',
      previewDetail: '你可能真正想要的，不是“做个接口”，而是让两边数据别再手工搬来搬去。'
    },
    automation: {
      code: 'automation',
      name: '自动化提效类需求',
      keywords: ['自动', '减少人工', '不用手动'],
      previewSentence: '把重复人工动作交给系统自动完成',
      previewDetail: '你可能真正想要的，不是“再少点人工”，而是找出最耗时的那一步直接自动化。'
    },
    general: {
      code: 'general',
      name: '通用业务需求',
      keywords: [],
      previewSentence: '把模糊的一句话整理成可提交的需求版本',
      previewDetail: '你可能还没想清楚具体做法，但至少可以先把“给谁用、哪里痛、希望系统做什么”说清楚。'
    }
  };
})(window);
