from __future__ import annotations

from pathlib import Path
import unittest
import json
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[2]


class PostMergeWorkflowContractTest(unittest.TestCase):
    def test_reconciliation_requires_a_successful_main_workflow_run(self) -> None:
        workflow = (ROOT / ".github/workflows/post-merge-release-evidence.yml").read_text()

        self.assertIn("github.event_name == 'workflow_run'", workflow)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", workflow)
        self.assertIn("github.event.workflow_run.head_branch == 'main'", workflow)
        self.assertNotIn("github.event_name == 'push' && github.ref", workflow)
        self.assertIn("MAIN_SHA: ${{ github.event.workflow_run.head_sha }}", workflow)

    def test_reconciliation_status_is_bound_to_the_workflow_run_main_sha(self) -> None:
        workflow = (ROOT / ".github/workflows/post-merge-release-evidence.yml").read_text()

        self.assertIn("sha: evidence.main_sha", workflow)
        self.assertNotIn("sha: context.sha, context: \"Post-Merge Release Evidence", workflow)

    def test_qualified_main_evidence_is_published_append_only_and_read_back(self) -> None:
        workflow = (ROOT / ".github/workflows/post-merge-release-evidence.yml").read_text()
        dispatch = (ROOT / ".github/workflows/home-assistant-release-artifact.yml").read_text()

        self.assertIn("contents: write", workflow)
        self.assertIn("contents: write", dispatch)
        self.assertIn("Produce redacted durable qualification evidence", workflow)
        self.assertIn("Publish append-only durable qualification evidence", workflow)
        self.assertIn("durable_evidence_release_tag_prefix", workflow)
        self.assertIn('tag="${DURABLE_EVIDENCE_RELEASE_TAG_PREFIX}-${CANDIDATE_SHA}"', workflow)
        self.assertIn("durable evidence collision: existing record will not be overwritten", workflow)
        self.assertIn("gh release download", workflow)
        self.assertLess(
            workflow.index("Publish append-only durable qualification evidence"),
            workflow.index("Publish exact-main-SHA reconciliation status"),
        )

    def test_actual_collector_paginates_369_files_and_rejects_incomplete_provenance(self):
        workflow = (ROOT / '.github/workflows/post-merge-release-evidence.yml').read_text()
        start = workflow.index('            async function collectCommitFiles(')
        end = workflow.index('            const {commit, files: commitFiles}', start)
        function = workflow[start:end]
        node = shutil.which('node')
        self.assertIsNotNone(node, 'Node is required for the actual GitHub-script collector regression')
        harness = r"""
const assert = require('node:assert/strict');
const sha='a'.repeat(40), parents=[{sha:'b'.repeat(40)}];
async function run(count, mutate=null) {
  const calls=[];
  const result=await collectCommitFiles(async options=>{
    calls.push(options);
    assert.equal(options.ref,sha);assert.equal(options.per_page,100);
    const from=(options.page-1)*100;
    const response={data:{sha,parents,files:Array.from({length:Math.min(100,Math.max(0,count-from))},
      (_,i)=>({filename:'file-'+(from+i)}))},headers:{}};
    if (from+100<count) response.headers.link='<https://api.github.com/next>; rel="next"';
    if(mutate)mutate(response,options.page);
    return response;
  },'owner','repo',sha);
  return {result,calls};
}
(async()=>{
  const {result,calls}=await run(369);
  assert.equal(result.files.length,369);assert.equal(calls.length,4);
  assert.equal(result.files[368].filename,'file-368');
  assert.equal((await run(0)).result.files.length,0);
  await assert.rejects(run(369,(r,p)=>{if(p===2)r.data.sha='c'.repeat(40)}));
  await assert.rejects(run(369,(r,p)=>{if(p===2)r.data.parents=[]}));
  await assert.rejects(run(369,(r,p)=>{if(p===2)r.data.files[0].filename='file-0'}));
  await assert.rejects(run(369,(r,p)=>{if(p===2)r.data.files=[]}));
  await assert.rejects(run(3000));
  process.stdout.write(JSON.stringify(result.files.map(f=>f.filename)));
})().catch(e=>{console.error(e);process.exitCode=1});
"""
        executed=subprocess.run([node,'-e',function+harness],capture_output=True,text=True,check=True,timeout=15)
        files=json.loads(executed.stdout)
        from tests.software_assurance.test_post_merge_reconciliation import request
        from tools.trusted_delivery.post_merge_reconciliation import reconcile
        payload=request()
        payload['originating_pr'].update(changed_files=files,main_changed_files=files)
        self.assertEqual(reconcile(payload)['decision'],'POST_MERGE_RELEASE_EVIDENCE_QUALIFIED')
        payload['originating_pr']['main_changed_files']=files[:300]
        self.assertNotEqual(reconcile(payload)['decision'],'POST_MERGE_RELEASE_EVIDENCE_QUALIFIED')
        self.assertIn('main_changed_files: commitFiles.map',workflow)
