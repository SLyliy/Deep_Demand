import json, app
text='?????????????????????????????'
for name, fn in [('context', app.retrieve_context), ('fast_fallback', app.build_fast_fallback_from_context), ('analysis', app.build_context_analysis)]:
    print('\n##', name)
    res=fn(text)
    print(json.dumps(res, ensure_ascii=False, indent=2)[:9000])
