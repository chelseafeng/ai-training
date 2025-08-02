import secrets

import fastapi
from fastapi import Depends, HTTPException, status
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.security import HTTPBasic, HTTPBasicCredentials

router = fastapi.APIRouter()
security = HTTPBasic()

def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, 'ict')
    correct_password = secrets.compare_digest(credentials.password, 'Admin@111111')
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

#
@router.get("/docs", include_in_schema=False)
# async def custom_swagger_ui_html(username: str = Depends(get_current_username)):
async def custom_swagger_ui_html():
    """
        自定义 Swagger UI 界面的路由处理函数。

        该函数返回一个自定义配置的 Swagger UI HTML 页面，其中包含指定的 OpenAPI 文档路径、标题、
        OAuth2 重定向 URL，以及自定义的 Swagger UI JavaScript 和 CSS 文件。

        返回:
            HTMLResponse: 包含自定义配置的 Swagger UI 页面。
        """
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="后台管理系统DOCS",
        oauth2_redirect_url="/docs/oauth2-redirect",
        # 在这里引入你的自定义 CSS 和 JS
        swagger_js_url="/static/custom-swagger-ui.js",
        swagger_css_url="/static/custom-swagger-ui.css",
    )
