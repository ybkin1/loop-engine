import pathlib, subprocess
BASE = pathlib.Path(__file__).resolve().parent.parent
def test_no_tracked_pyc():
    r = subprocess.run([chr(103)+chr(105)+chr(116),chr(108)+chr(115)+chr(45)+chr(102)+chr(105)+chr(108)+chr(101)+chr(115),chr(45)+chr(45),chr(42)+chr(46)+chr(112)+chr(121)+chr(99)],capture_output=True,text=True,cwd=str(BASE))
    assert not r.stdout.strip(), chr(102)+chr(39)+chr(84)+chr(114)+chr(97)+chr(99)+chr(107)+chr(101)+chr(100)+chr(32)+chr(112)+chr(121)+chr(99)+chr(58)+chr(32)+chr(123)+chr(125)+chr(39)+chr(46)+chr(102)+chr(111)+chr(114)+chr(109)+chr(97)+chr(116)+chr(40)+chr(114)+chr(46)+chr(115)+chr(116)+chr(100)+chr(111)+chr(117)+chr(116))
def test_version_consistency():
    vs=set()
    for p in [BASE/chr(99)+chr(111)+chr(100)+chr(101)+chr(120)+chr(95)+chr(108)+chr(111)+chr(111)+chr(112)+chr(47)+chr(95)+chr(95)+chr(105)+chr(110)+chr(105)+chr(116)+chr(95)+chr(95)+chr(46)+chr(112)+chr(121),BASE/chr(108)+chr(111)+chr(111)+chr(112)+chr(95)+chr(99)+chr(111)+chr(114)+chr(101)+chr(47)+chr(95)+chr(95)+chr(105)+chr(110)+chr(105)+chr(116)+chr(95)+chr(95)+chr(46)+chr(112)+chr(121)]:
        for line in p.read_text().splitlines():
            if chr(95)+chr(95)+chr(118)+chr(101)+chr(114)+chr(115)+chr(105)+chr(111)+chr(110)+chr(95)+chr(95) in line:
                vs.add(line.split(chr(61))[-1].strip().strip(chr(39)+chr(34)))
    t=(BASE/chr(112)+chr(121)+chr(112)+chr(114)+chr(111)+chr(106)+chr(101)+chr(99)+chr(116)+chr(46)+chr(116)+chr(111)+chr(109)+chr(108)).read_text()
    for line in t.splitlines():
        if chr(118)+chr(101)+chr(114)+chr(115)+chr(105)+chr(111)+chr(110) in line and chr(61) in line:
            vs.add(line.split(chr(61))[-1].strip().strip(chr(39)+chr(34)))
    assert len(vs)==1,chr(102)+chr(39)+chr(86)+chr(101)+chr(114)+chr(115)+chr(105)+chr(111)+chr(110)+chr(32)+chr(109)+chr(105)+chr(115)+chr(109)+chr(97)+chr(116)+chr(99)+chr(104)+chr(58)+chr(32)+chr(123)+chr(118)+chr(115)+chr(125)+chr(39)