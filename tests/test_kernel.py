import tempfile, unittest
from pathlib import Path
from asya_foundation.kernel import GovernanceError, GovernanceKernel, Risk, Store, TaskRequest, TaskState

class KernelTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.store=Store(Path(self.tmp.name)/"test.sqlite3"); self.k=GovernanceKernel(self.store,0.0)
 def tearDown(self): self.tmp.cleanup()
 def req(self,**kw):
  d=dict(title="test",objective="verify",project_id="asya",idempotency_key="test-1"); d.update(kw); return TaskRequest(**d)
 def test_idempotency(self):
  a=self.k.submit(self.req()); b=self.k.submit(self.req()); self.assertEqual(a["task_id"],b["task_id"]); self.assertFalse(b["created"])
 def test_high_risk_approval(self):
  t=self.k.submit(self.req(risk=Risk.HIGH,idempotency_key="high")); self.assertTrue(t["approval_required"])
  with self.assertRaises(GovernanceError): self.k.execute_local(t["task_id"],"builder",{})
  self.k.approve(t["task_id"],"human",True); self.assertEqual(self.store.get(t["task_id"])["state"],TaskState.AUTHORIZED.value)
 def test_budget(self):
  with self.assertRaises(GovernanceError): self.k.submit(self.req(estimated_cost_usd=0.01))
 def test_evidence_gate(self):
  t=self.k.submit(self.req()); out=self.k.execute_local(t["task_id"],"builder",{"acceptance_criteria":["test"],"tests_passed":True,"evidence_ref":"sha256:abc"})
  self.assertEqual(out["evaluation"],"passed")
 def test_no_self_certification(self):
  t=self.k.submit(self.req()); out=self.k.execute_local(t["task_id"],"builder",{"tests_passed":True})
  self.assertEqual(out["evaluation"],"failed")
 def test_audit_hash_chain(self):
  t=self.k.submit(self.req()); self.k.execute_local(t["task_id"],"builder",{"acceptance_criteria":["x"],"tests_passed":True,"evidence_ref":"sha256:abc"})
  self.assertTrue(self.store.verify_chain())
 def test_invalid_transition(self):
  t=self.k.submit(self.req())
  with self.assertRaises(GovernanceError): self.store.transition(t["task_id"],TaskState.COMPLETED,"builder")

if ( __name__ == "__main__"): unittest.main()
