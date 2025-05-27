from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import logging
from typing import Optional, Union, Dict, Any
import json

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Telegram API Proxy")

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cấu hình Telegram API
TELEGRAM_API_URL = "https://api.telegram.org"

@app.get("/")
async def root():
    return {
        "message": "Telegram API Proxy đang hoạt động",
        "usage": "Sử dụng URL này thay thế cho api.telegram.org",
        "example": "https://api.myserver.org/bot<token>/sendMessage"
    }

async def make_request(
    method: str,
    url: str,
    params: Dict[str, Any],
    body: Optional[Union[Dict[str, Any], bytes]] = None
) -> httpx.Response:
    """Thực hiện request đến Telegram API"""
    try:
        # Tạo headers mới
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive"
        }
        
        if body:
            if isinstance(body, dict):
                headers["Content-Type"] = "application/json"
            else:
                headers["Content-Type"] = "application/x-www-form-urlencoded"
        
        logger.info(f"Request headers: {headers}")
        logger.info(f"Request body: {body}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method in ["POST", "PUT", "PATCH"]:
                if isinstance(body, dict):
                    response = await client.request(
                        method=method,
                        url=url,
                        params=params,
                        headers=headers,
                        json=body
                    )
                else:
                    response = await client.request(
                        method=method,
                        url=url,
                        params=params,
                        headers=headers,
                        content=body
                    )
            else:
                response = await client.request(
                    method=method,
                    url=url,
                    params=params,
                    headers=headers
                )
            response.raise_for_status()
            return response
    except Exception as e:
        logger.error(f"Request failed: {str(e)}")
        raise

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def proxy_request(request: Request, path: str):
    try:
        # Lấy thông tin request
        method = request.method
        params = dict(request.query_params)
        
        # Lấy body nếu có
        body = None
        if method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.json()
            except:
                body = await request.body()
        
        # Tạo URL đích
        target_url = f"{TELEGRAM_API_URL}/{path}"
        logger.info(f"Processing {method} request to {target_url}")
        
        try:
            # Thực hiện request
            response = await make_request(method, target_url, params, body)
            
            # Lấy response data
            response_data = None
            if response.headers.get("content-type", "").startswith("application/json"):
                response_data = response.json()
            
            # Tạo response headers mới
            response_headers = {
                "content-type": response.headers.get("content-type", "application/json"),
                "access-control-allow-origin": "*",
                "access-control-allow-methods": "*",
                "access-control-allow-headers": "*"
            }
            
            # Trả về response
            if response_data is not None:
                return JSONResponse(
                    content=response_data,
                    status_code=response.status_code,
                    headers=response_headers
                )
            else:
                return StreamingResponse(
                    response.iter_bytes(),
                    media_type=response.headers.get("content-type"),
                    status_code=response.status_code,
                    headers=response_headers
                )
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"error": f"Lỗi khi chuyển tiếp request: {str(e)}"}
            )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Lỗi không xác định: {str(e)}"}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=2552) 