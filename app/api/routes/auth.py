from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.sqlite_service import get_db
from app.services.authentication import login_user, logout_user, verify_token

router = APIRouter()

# Định nghĩa các model request/response
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_at: Any
    user_id: str
    username: str
    role: Optional[str] = None

class LogoutRequest(BaseModel):
    token: str

class SuccessResponse(BaseModel):
    success: bool
    message: str

# Endpoint đăng nhập
@router.post("/login", response_model=TokenResponse)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    Đăng nhập và nhận token xác thực
    """
    result = await login_user(
        username=login_data.username,
        password=login_data.password,
        db=db
    )
    return result

# Endpoint đăng xuất
@router.post("/logout", response_model=SuccessResponse)
async def logout(logout_data: LogoutRequest, db: Session = Depends(get_db)):
    """
    Đăng xuất (thu hồi token)
    """
    result = await logout_user(token=logout_data.token, db=db)
    return result

# Hàm dependency để xác thực token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    required: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Xác thực token và trả về thông tin người dùng
    
    Args:
        token: Token xác thực từ header
        db: Database session
        required: Nếu True, sẽ raise HTTPException khi không có token hoặc token không hợp lệ
                 Nếu False, sẽ trả về None khi không có token hoặc token không hợp lệ
    
    Returns:
        Dict chứa thông tin người dùng hoặc None nếu không có token và required=False
    """
    if not token:
        if required:
            raise HTTPException(status_code=401, detail="Token không được cung cấp")
        return None
    
    try:
        return await verify_token(token=token, db=db)
    except HTTPException as e:
        if required:
            raise e
        return None

async def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[Dict[str, Any]]:
    """
    Dependency function để xác thực token tùy chọn
    Trả về None nếu không có token hoặc token không hợp lệ
    """
    return await get_current_user(token=token, db=db, required=False)

# Dependency để xác thực token từ header Authorization
async def get_user_from_header(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Xác thực token từ header và trả về thông tin người dùng
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header không được cung cấp")
    
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Authorization header phải là Bearer token")
    
    return await verify_token(token=token, db=db)

# Dependency để kiểm tra quyền admin
async def require_admin(user_data: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Kiểm tra xem người dùng hiện tại có quyền admin không
    """
    role = user_data.get("role")
    if role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Không có quyền thực hiện hành động này. Yêu cầu quyền admin."
        )
    return user_data

async def get_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Kiểm tra quyền admin của người dùng
    """
    if not current_user.get("role") or current_user["role"].lower() != "admin":
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền thực hiện hành động này. Chỉ admin mới được phép."
        )
    return current_user 