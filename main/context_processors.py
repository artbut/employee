from datetime import datetime

def global_context(request):
    return {
        'current_year': datetime.now().year,
    }