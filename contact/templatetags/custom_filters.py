from django import template

register = template.Library()

@register.filter
def format_seconds(value):
    try:
        seconds = int(value)
        return f"{seconds // 60}m {seconds % 60}s"
    except:
        return "0m 0s"
