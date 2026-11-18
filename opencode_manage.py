"""Small OpenCode config editor: providers, custom models and MCP servers."""
import datetime
import json
import os
from pathlib import Path
import re
import tempfile


def config_path():
    """Discover the OpenCode config, respecting explicit and XDG overrides."""
    override = os.environ.get('OMO_OPENCODE_CONFIG')
    if override:
        return Path(override).expanduser()
    custom = os.environ.get('OPENCODE_CONFIG_DIR')
    if custom:
        base = Path(custom).expanduser()
    else:
        base = Path(os.environ.get('XDG_CONFIG_HOME', '~/.config')).expanduser() / 'opencode'
    for name in ('opencode.jsonc', 'opencode.json'):
        if (base / name).is_file():
            return base / name
    return base / 'opencode.json'


def write_target():
    """Follow config symlinks so the link itself is preserved on write."""
    path = config_path()
    if path.is_symlink():
        try:
            return path.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise ValueError(f'Cannot resolve config symlink {path}: {exc}') from exc
    return path


def _mask(text):
    chars=list(text); i=0
    while i<len(text):
        if text[i]=='"':
            i+=1
            while i<len(text):
                if text[i]=='\\': i+=2
                elif text[i]=='"': i+=1;break
                else:i+=1
        elif text.startswith('//',i):
            j=text.find('\n',i);j=len(text) if j<0 else j
            for k in range(i,j):chars[k]=' '
            i=j
        elif text.startswith('/*',i):
            j=text.find('*/',i+2)
            if j<0:raise ValueError('Unclosed JSONC comment')
            for k in range(i,j+2):chars[k]=' '
            i=j+2
        else:i+=1
    return ''.join(chars)


def parse(text):
    masked=_mask(text)
    # Ignore trailing commas outside strings.
    outside=list(masked)
    i=0
    while i<len(masked):
        if masked[i]=='"':
            start=i;i+=1
            while i<len(masked):
                if masked[i]=='\\':i+=2
                elif masked[i]=='"':i+=1;break
                else:i+=1
            for j in range(start,i):outside[j]='X'
        else:i+=1
    for match in re.finditer(r',(?=\s*[}\]])',''.join(outside)):
        masked=masked[:match.start()]+' '+masked[match.start()+1:]
    result=json.loads(masked)
    if not isinstance(result,dict):raise ValueError('OpenCode config must be an object')
    return result


def load():
    path=config_path()
    source=path.read_text(encoding='utf-8') if path.exists() else '{}\n'
    return source,parse(source)


def _section_span(source,section):
    """Locate top-level section using JSONC masked offsets, preserving other sections."""
    masked=_mask(source)
    decoder=json.JSONDecoder()
    i=0
    def skip(i):
        while i<len(masked) and masked[i].isspace():i+=1
        return i
    i=skip(i)
    if masked[i]!='{':raise ValueError('Invalid root')
    i+=1
    while True:
        i=skip(i)
        if masked[i]=='}':return None
        key,end=decoder.raw_decode(masked,i)
        if not isinstance(key,str):raise ValueError('Invalid key')
        i=skip(end)
        if masked[i]!=':':raise ValueError('Missing colon')
        start=skip(i+1)
        # decoder.raw_decode cannot parse nested trailing commas, so scan balanced braces.
        pos=start; depth=0; quote=False; escaped=False
        while pos<len(masked):
            c=masked[pos]
            if quote:
                if escaped:escaped=False
                elif c=='\\':escaped=True
                elif c=='"':quote=False
            elif c=='"':quote=True
            elif c in '[{':depth+=1
            elif c in ']}':
                if depth==0:break
                depth-=1
            elif c==',' and depth==0:break
            pos+=1
        end=pos
        while end>start and masked[end-1].isspace():end-=1
        if key==section:return start,end
        i=skip(pos)
        if masked[i]==',':i+=1
        elif masked[i]=='}':return None
        else:raise ValueError('Invalid root separator')


def save_section(section,value,yes=False):
    if section not in ('provider','mcp','model'):raise ValueError('Unsupported section')
    source,data=load()
    if not yes:raise ValueError('Explicit confirmation required')
    path=config_path()
    replacement=json.dumps(value,indent=2,ensure_ascii=False)
    span=_section_span(source,section)
    if span:
        a,b=span
        updated=source[:a]+replacement+source[b:]
    else:
        pos=_mask(source).rfind('}')
        prefix=source[:pos].rstrip()
        comma='' if prefix.rstrip().endswith(('{',',')) else ','
        updated=prefix+comma+'\n  '+json.dumps(section)+': '+replacement.replace('\n','\n  ')+ '\n'+source[pos:]
    parse(updated)
    target=write_target()
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        backup=target.with_name(target.name+'.bak-'+stamp)
        backup.write_bytes(target.read_bytes())
        os.chmod(backup,0o600)
    fd,tmp=tempfile.mkstemp(prefix='.'+target.name+'.',dir=target.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            f.write(updated);f.flush();os.fsync(f.fileno())
        os.chmod(tmp,target.stat().st_mode & 0o777 if target.exists() else 0o600)
        os.replace(tmp,target)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    return path


def mutate(section,name,value=None,operation='set'):
    _,data=load()
    group=data.get(section,{})
    if not isinstance(group,dict):raise ValueError(section+' must be an object')
    group=dict(group)
    if operation=='delete':
        if name not in group:raise ValueError('Entry not found: '+name)
        del group[name]
    elif operation=='set':
        if not isinstance(value,dict):raise ValueError('Entry must be a JSON object')
        group[name]=value
    elif operation=='toggle':
        if section!='mcp' or name not in group or not isinstance(group[name],dict):raise ValueError('MCP not found')
        group[name]={**group[name],'enabled':not group[name].get('enabled',True)}
    else:raise ValueError('Unknown operation')
    return save_section(section,group,yes=True)


def provider_model(provider,name,value=None,operation='set'):
    _,data=load()
    providers=data.get('provider',{})
    if not isinstance(providers,dict):raise ValueError('Invalid provider section')
    providers=dict(providers)
    entry=dict(providers.get(provider,{}))
    models=dict(entry.get('models',{}))
    if operation=='delete':
        if name not in models:raise ValueError('Model not found')
        del models[name]
    else:
        if not isinstance(value,dict):raise ValueError('Model definition must be a JSON object')
        models[name]=value
    entry['models']=models;providers[provider]=entry
    return save_section('provider',providers,yes=True)
