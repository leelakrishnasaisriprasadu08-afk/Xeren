import sys
sys.path.insert(0, "src")
from xeren.core.runtime import XerenCore
from xeren.plugins.verification.schemas import VerificationInput, VerificationOperation

c = XerenCore()
inp = VerificationInput(operation=VerificationOperation.FINAL_RESPONSE_VERIFICATION, candidate="test output")
r = c.execute_plugin("verification", inp)
print("EXEC_RES success:", r.success)
print("EXEC_RES error:", r.error)
print("EXEC_RES output:", type(r.output), r.output)
