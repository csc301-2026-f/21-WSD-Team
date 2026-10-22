def success_response(data):
    return {
        "status" : "success",
        "data" : data,
        "error" : None
    }

def fail_response(code, message):
    return {
        "status" : "error",
        "data" : None,
        "error" : {
            "code" : code,
            "message" : message
        }
    }

def unsupported_response(message):
    return fail_response("UNSUPPORTED", message)