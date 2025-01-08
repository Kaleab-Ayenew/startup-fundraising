from pydantic import BaseModel, EmailStr
from typing import Optional, List

class User(BaseModel):
    email: EmailStr
    name: str

# =======================#
#   Founder Schemas      #
# =======================#
class FounderCreate(BaseModel):
    fullName: str
    email: EmailStr
    password: str
    contact_details: Optional[str] = None
    industry: Optional[str] = None
    role: Optional[str] = None
    companyName: Optional[str] = None

class FounderUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    contact_details: Optional[str] = None

class FounderOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    contact_details: Optional[str] = None

    class Config:
        orm_mode = True

# =======================#
#   Investor Schemas     #
# =======================#
class InvestorCreate(BaseModel):
    fullName: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    investmentFocus: Optional[str] = None
    investmentBudget: Optional[str] = None
    investmentSector: Optional[str] = None
    investmentExperience: Optional[str] = None
    linkedInProfile: Optional[str] = None
    role: Optional[str] = None

class InvestorUpdate(BaseModel):
    fullName: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    investmentFocus: Optional[str] = None
    investmentBudget: Optional[str] = None
    investmentSector: Optional[str] = None
    investmentExperience: Optional[str] = None
    linkedInProfile: Optional[str] = None
    role: Optional[str] = None

class InvestorOut(BaseModel):
    id: int
    name: str
    email: EmailStr

    class Config:
        orm_mode = True

# =======================#
#   Project Schemas      #
# =======================#
class ProjectCreate(BaseModel):
    name: str
    description: str
    target_amount: float
    image_url: Optional[str] = None

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    target_amount: Optional[float] = None
    image_url: Optional[str] = None

class ProjectOut(BaseModel):
    id: int
    name: str
    description: str
    target_amount: float
    image_url: Optional[str] = None
    founder_id: int

    class Config:
        orm_mode = True

# =======================#
#  Investment Schemas    #
# =======================#
class InvestmentCreate(BaseModel):
    project_id: int
    amount: float

class InvestmentUpdate(BaseModel):
    project_id: Optional[int] = None
    amount: Optional[float] = None

class InvestmentOut(BaseModel):
    id: int
    amount: float
    project_id: int
    investor_id: int

    class Config:
        orm_mode = True

# =======================#
#     Update Schemas     #
# =======================#
class UpdateCreate(BaseModel):
    project_id: int
    content: str

class UpdateUpdate(BaseModel):
    content: Optional[str] = None

class UpdateOut(BaseModel):
    id: int
    content: str
    project_id: int

    class Config:
        orm_mode = True

# =======================#
#     Admin Schemas      #
# =======================#
class AdminCreate(BaseModel):
    email: EmailStr
    password: str

class AdminUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None

class AdminOut(BaseModel):
    id: int
    email: EmailStr

    class Config:
        orm_mode = True
