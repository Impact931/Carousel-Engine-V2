"""
Ultra-minimal test for Vercel Python deployment
"""

def handler(request):
    """Simple HTTP handler for Vercel"""
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
        },
        'body': '{"message": "Basic Python handler working", "status": "success"}'
    }

# Alternative WSGI-style entry point
def application(environ, start_response):
    status = '200 OK'
    headers = [('Content-Type', 'application/json')]
    start_response(status, headers)
    return [b'{"message": "WSGI handler working"}']