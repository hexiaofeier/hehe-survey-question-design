"""Validate this standalone Skill package with the Python standard library."""
from pathlib import Path
from urllib.parse import unquote
import hashlib, json, re, sys, zipfile, xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
NAME='hehe-survey-question-design'
SKILL=ROOT/'skills'/NAME
errors=[]
def check(ok,message):
    if not ok:errors.append(message)
def read(p):return p.read_text(encoding='utf-8-sig')

required=['README.md','LICENSE','release-manifest.json','docs/images/survey-design-cover.png','docs/images/questionnaire-deliverables.png']
for name in required:check((ROOT/name).is_file(),'Missing: '+name)
if errors:sys.exit('\n'.join(errors))
m=json.loads(read(ROOT/'release-manifest.json'))
check(m['entry_skill']==NAME and m['install_policy']=='standalone','Incorrect entry or install policy')
check(m['required_skills']==[],'Unexpected required Skill dependency')
check(sorted(p.name for p in (ROOT/'skills').iterdir())==[NAME],'Unexpected Skill folder')
check(re.search(r'^name: '+NAME+r'$',read(SKILL/'SKILL.md'),re.M) is not None,'Frontmatter name mismatch')
check(len(m['required_local_files'])==8,'Incomplete runtime file list')
for name in m['required_local_files']:
    p=SKILL/name;check(p.is_file(),'Missing runtime: '+name)
    if p.is_file():check(hashlib.sha256(p.read_bytes()).hexdigest()==m['public_sha256'].get(name),'Hash mismatch: '+name)
check(set(p.relative_to(SKILL).as_posix() for p in SKILL.rglob('*') if p.is_file())==set(m['required_local_files']),'Unexpected runtime files')

for p in ROOT.rglob('*'):
    rel=p.relative_to(ROOT)
    if '.git' in rel.parts:continue
    check(not any(x in {'_本地维护','90_历史备份','__pycache__','node_modules'} for x in rel.parts),'Unexpected private/cache path: '+str(rel))
    if not p.is_file():continue
    check('_CO' not in p.name,'Local filename suffix: '+str(rel))
    if p.suffix not in {'.md','.json','.py','.yml','.yaml','.txt'} or p==Path(__file__).resolve():continue
    text=read(p)
    check(re.search(r'[A-Z]:[\\/](?:Users|LenovoSoftstore)[\\/]',text,re.I) is None,'Local absolute path: '+str(rel))
    check(re.search(r'(?<![\w-])(?:tanzi-pro|agentkey)(?![\w-])',text,re.I) is None,'Private capability: '+str(rel))
    check(re.search(r'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|sk-[A-Za-z0-9]{30,})',text) is None,'Possible credential: '+str(rel))
    if p.suffix=='.md':
        check(re.search(r'\$survey-question-design\b|/survey-question-design(?:\s|$)',text) is None,'Old invocation name: '+str(rel))
        for url in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',text):
            if url.startswith('#') or re.match(r'^[a-z]+:',url,re.I):continue
            target=unquote(url.strip('<>').split('#')[0]);dst=(p.parent/target).resolve()
            check(dst.is_relative_to(ROOT.resolve()) and dst.exists(),'Broken/escaping link: '+str(rel)+' -> '+url)
            if p.is_relative_to(SKILL):check(dst.is_relative_to(SKILL.resolve()),'Runtime link leaves install folder: '+url)

ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

def txt(node):
    return ''.join(t.text or '' for t in node.findall('.//w:t',ns))

def parse_detail(md):
    # Retain document order and every explanatory paragraph.
    tokens=[];questions={}
    for block in re.split(r'\n\s*\n',md.strip()):
        lines=block.splitlines();hit=re.match(r'^(\d+)、(.*)$',lines[0])
        if not hit:
            tokens.extend(('text',re.sub(r'^#{1,6}\s+','',line)) for line in lines if line.strip())
            continue
        number,rest=int(hit[1]),hit[2];split=rest.find('[')
        title,tags=(rest,'') if split<0 else (rest[:split],rest[split:])
        raw=lines[1:];rows=[];options=raw
        if '行项目：' in raw or '列选项：' in raw:
            check(raw.count('行项目：')==raw.count('列选项：')==1,f'Malformed matrix: Q{number}')
            if raw.count('行项目：')==raw.count('列选项：')==1:
                a,b=raw.index('行项目：'),raw.index('列选项：')
                check(a==0 and b>a,f'Matrix row/column order: Q{number}')
                rows,options=raw[a+1:b],raw[b+1:]
        q=dict(number=number,title=title,tags=tags,raw=raw,rows=rows,options=options)
        check(number not in questions,f'Duplicate detail question: Q{number}')
        questions[number]=q;tokens.append(('question',q))
    check(list(questions)==list(range(1,len(questions)+1)),'Noncontinuous detail question numbers')
    return tokens,questions

def check_word(path,tokens):
    # Accept both paragraph options and native tables; match all content.
    external=0
    with zipfile.ZipFile(path) as z:
        body=ET.fromstring(z.read('word/document.xml')).find('w:body',ns)
        for name in z.namelist():
            if not name.endswith(('.xml','.rels')):continue
            text=z.read(name).decode('utf-8','replace')
            check(re.search(r'(?:[A-Z]:[\\/](?:Users|LenovoSoftstore)[\\/]|file://)',text,re.I) is None,
                  f'Local path inside Word: {path.parent.name}!{name}')
            check(re.search(r'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|sk-[A-Za-z0-9]{30,})',text) is None,
                  f'Possible credential inside Word: {path.parent.name}!{name}')
            if name.endswith('.rels'):
                for rel in ET.fromstring(text):
                    if rel.get('TargetMode')!='External':continue
                    external+=1;target=unquote(rel.get('Target',''))
                    check(re.match(r'^(?:https?://|mailto:)',target,re.I) is not None,
                          f'Unsupported external Word relationship: {path.parent.name}!{name}')
    nodes=[n for n in body if n.tag.endswith('}tbl') or (n.tag.endswith('}p') and txt(n).strip())]
    index=0
    def paragraph(expected,label):
        nonlocal index
        check(index<len(nodes),f'Missing Word text: {label}')
        if index>=len(nodes):return
        node=nodes[index];index+=1
        check(node.tag.endswith('}p') and txt(node)==expected,f'Word text differs: {label}')
    for kind,value in tokens:
        if kind=='text':paragraph(value,path.parent.name+' '+value[:40]);continue
        q=value;label=f'{path.parent.name} Q{q["number"]}'
        stem=f'{q["number"]}、{q["title"]}'
        if index<len(nodes) and txt(nodes[index])==stem+q['tags']:
            paragraph(stem+q['tags'],label+' stem/tags')
        else:
            paragraph(stem,label+' stem')
            if q['tags']:paragraph(q['tags'],label+' tags')
        if not q['raw']:continue
        if index<len(nodes) and nodes[index].tag.endswith('}tbl'):
            table=nodes[index];index+=1
            cells=[[txt(c) for c in row.findall('w:tc',ns)] for row in table.findall('w:tr',ns)]
            if q['rows']:
                check(bool(cells) and cells[0]==['评价项目']+q['options'],label+' matrix columns differ')
                check([row[0] for row in cells[1:] if row]==q['rows'],label+' matrix rows differ')
                check(all(row[1:]==['○']*len(q['options']) for row in cells[1:]),label+' matrix answer cells differ')
            else:check(cells==[[option] for option in q['options']],label+' table options differ')
        else:
            for line in q['raw']:paragraph(line,label+' options')
    check(index==len(nodes),'Unexpected trailing Word text: '+path.parent.name)
    return external

def check_import(path,questions):
    found={};count=0;opening=0
    for block in re.split(r'\n\s*\n',read(path).strip()):
        lines=block.splitlines();hit=re.match(r'^(\d+)\.\s+(.*)$',lines[0])
        if not hit:
            opening+=1
            check(not found and opening==1 and len(lines)==1,'Unexpected import text: '+path.parent.name)
            continue
        number,heading=int(hit[1]),hit[2]
        check(number in questions and number not in found,f'Unknown/duplicate import Q{number}')
        if number not in questions:continue
        q=questions[number];matrix=heading.endswith('[矩阵题]');multi=heading.endswith('[多选题]')
        heading=re.sub(r'\[(?:多选题|矩阵题)\]$','',heading)
        expected=q['title']
        if not q['raw'] and not expected.endswith('：'):
            expected=expected.rstrip('？。')+'：'
        check(heading==expected,f'Import stem differs: {path.parent.name} Q{number}')
        if q['rows']:
            check(matrix,f'Missing matrix import type: Q{number}')
            expected_lines=[' '.join(q['options'])]+q['rows']
        else:
            check(not matrix,f'Unexpected matrix type: Q{number}')
            check(multi==('[多选题]' in q['tags']),f'Multiselect import type differs: Q{number}')
            expected_lines=q['options']
        check(lines[1:]==expected_lines,f'Import options/rows differ: {path.parent.name} Q{number}')
        for option in q['options']+q['rows']:
            check(' ' not in option and not re.match(r'^(?:[A-Da-d][.、)]|c\d{2}[.、)])',option),f'Option import formatting: Q{number}')
        found[number]=True;count+=len(q['options'])+len(q['rows'])
    check(list(found)==list(questions),'Import question coverage/order differs: '+path.parent.name)
    return count

example_sets=m.get('example_sets') or [dict(m['examples'],directory='examples/age-friendly-renovation')]
summaries=[]
for example in example_sets:
    directory=(ROOT/example['directory']).resolve()
    check(directory.is_relative_to(ROOT.resolve()),'Example directory escapes repository')
    if not directory.is_relative_to(ROOT.resolve()):continue
    for name in example['files']:
        path=ROOT/name if str(name).startswith('examples/') else directory/name
        check(path.resolve().is_relative_to(ROOT.resolve()) and path.is_file(),'Missing/escaping example file: '+str(name))
    paths=[directory/'questionnaire-design.md',directory/'questionnaire-design.docx',directory/'questionnaire-import.md']
    for path in paths:check(path.is_file(),'Missing questionnaire example: '+str(path.relative_to(ROOT)))
    if not all(p.is_file() for p in paths):continue
    try:
        tokens,questions=parse_detail(read(paths[0]))
        check(len(questions)==example['questions'],'Example question count differs: '+directory.name)
        external=check_word(paths[1],tokens);options=check_import(paths[2],questions)
        if 'options' in example:check(options==example['options'],'Example option count differs: '+directory.name)
        summaries.append(f'{directory.name}: {len(questions)} questions, complete MD/Word/import content, {external} external Word links')
    except (OSError,ValueError,KeyError,ET.ParseError,zipfile.BadZipFile) as exc:
        errors.append('Cannot validate example '+directory.name+': '+str(exc))
if errors:
    print('\n'.join('ERROR: '+e for e in errors));sys.exit(1)
print('PASS: standalone name, 8 runtime files/hashes, package links and public boundaries.')
for summary in summaries:print('PASS: '+summary)
