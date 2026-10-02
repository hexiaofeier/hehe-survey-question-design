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

ex=ROOT/'examples/age-friendly-renovation'
md=read(ex/'questionnaire-design.md').rstrip()
pure=read(ex/'questionnaire-import.md').rstrip()
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
with zipfile.ZipFile(ex/'questionnaire-design.docx') as z:
    xml=ET.fromstring(z.read('word/document.xml'))
paragraphs=[''.join(t.text or '' for t in p.findall('.//w:t',ns)) for p in xml.findall('./w:body/w:p',ns)]
check(paragraphs==[re.sub(r'^#{1,2} ','',s) for s in md.splitlines()],'MD/Word paragraphs differ')
detail={}
for block in md.split('\n\n'):
    lines=block.splitlines();match=re.match(r'^(\d+)、([^\[]+)',lines[0]) if lines else None
    if match:detail[int(match[1])]=(match[2],lines[1:])
count=0
for block in pure.split('\n\n')[1:]:
    lines=block.splitlines();match=re.match(r'^(\d+)\. (.*?)(?:\[多选题\])?$',lines[0])
    check(match is not None,'Invalid import question header')
    if not match:continue
    number=int(match[1]);check(detail.get(number)==(match[2],lines[1:]),'Example mismatch: Q'+str(number))
    for option in lines[1:]:check(' ' not in option and not re.match(r'^[A-Da-d][.、)]',option),'Option import formatting: Q'+str(number))
    count+=len(lines)-1
check(len(detail)==m['examples']['questions']==38 and count==m['examples']['options']==225,'Example size mismatch')
if errors:
    print('\n'.join('ERROR: '+e for e in errors));sys.exit(1)
print('PASS: standalone name, 8 runtime files and hashes, package links/cleanliness, 38 questions/225 options, MD/Word consistency.')
