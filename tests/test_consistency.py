import pathlib
import subprocess
BASE=pathlib.Path(__file__).resolve().parent.parent
def test_no_tracked_pyc():
 r=subprocess.run([chr(103)+chr(105)+chr(116),chr(108)+chr(115)+chr(45)+chr(102)+chr(105)+chr(108)+chr(101)+chr(115),chr(45)+chr(45),chr(42)+chr(46)+chr(112)+chr(121)+chr(99)],capture_output=True,text=True,cwd=str(BASE))
 assert r.stdout.strip()==chr(39)+chr(39)
