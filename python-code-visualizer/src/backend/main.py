
from fastapi import FastAPI
from pydantic import BaseModel
import sys
import io
from contextlib import redirect_stdout

app = FastAPI()

class Code(BaseModel):
    code: str

@app.post("/execute")
async def execute(code: Code):
    """
    Executes Python code and captures the execution trace.
    """
    trace = []
    
    def tracer(frame, event, arg):
        if event == 'line':
            line_no = frame.f_lineno
            local_vars = frame.f_locals
            
            # Create a serializable copy of local_vars
            serializable_vars = {}
            for k, v in local_vars.items():
                try:
                    # Attempt to serialize, if it fails, convert to string
                    serializable_vars[k] = {
                        "value": v,
                        "type": str(type(v))
                    }
                except:
                    serializable_vars[k] = {
                        "value": str(v),
                        "type": str(type(v))
                    }

            trace.append({
                "line": line_no,
                "variables": serializable_vars,
                "call_stack": [] # Placeholder for now
            })
        return tracer

    # Capture stdout
    output_io = io.StringIO()
    with redirect_stdout(output_io):
        try:
            # Use a new dictionary for the execution context
            exec_globals = {}
            sys.settrace(tracer)
            exec(code.code, exec_globals)
            sys.settrace(None)
        except Exception as e:
            return {"error": str(e), "trace": trace}
    
    output = output_io.getvalue()
    
    return {"trace": trace, "output": output}
