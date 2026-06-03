import os

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")
templates.env.globals["ga_id"] = os.environ.get("GOOGLE_ANALYTICS_ID", "")
