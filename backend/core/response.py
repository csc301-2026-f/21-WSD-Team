# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
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