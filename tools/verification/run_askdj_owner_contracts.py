"""Run existing owning tests with a bounded identity-only result receipt."""
import json
from pathlib import Path
import sys
import unittest


class Result(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.executed=[]
        self.case_outcomes=[]
    def addSubTest(self,test,subtest,err):
        case=subtest.params.get('case')
        if isinstance(case,str):
            self.case_outcomes.append({'id':case,'status':'PASS' if err is None else 'FAIL'})
        super().addSubTest(test,subtest,err)
    def startTest(self,test):
        self.executed.append(test.id())
        super().startTest(test)


def main():
    pattern=sys.argv[1]
    output=Path(sys.argv[2])
    suite=unittest.defaultTestLoader.discover('tests',pattern=pattern)
    result=unittest.TextTestRunner(resultclass=Result,verbosity=0).run(suite)
    report={'pattern':pattern,'tests_run':result.testsRun,'executed':result.executed,
            'failed':[test.id() for test,_ in result.failures],
            'errors':[test.id() for test,_ in result.errors],
            'skipped':[test.id() for test,_ in result.skipped],
            'paid_attempts':0,'network':'none','case_outcomes':result.case_outcomes}
    report['status']='PASS' if result.wasSuccessful() and result.testsRun>0 and not result.skipped else 'FAIL'
    output.write_text(json.dumps(report,indent=2)+'\n')
    return 0 if report['status']=='PASS' else 1


if __name__=='__main__':
    raise SystemExit(main())
