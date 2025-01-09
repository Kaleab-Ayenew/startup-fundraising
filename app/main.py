
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.staticfiles import StaticFiles

from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta

from .auth import (
    authenticate_user,
    create_access_token,
    get_current_active_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import shutil
import stripe
import json
from datetime import datetime

from .database import Base, engine, get_db
from .config import ADMIN_CREATION_TOKEN, STRIPE_SECRET_KEY, STATIC_FILES_DIR
from . import models, schema, utils, auth

# Create DB tables at startup (For dev/demo. In production, use migrations.)
Base.metadata.create_all(bind=engine)

# FastAPI init
app = FastAPI(title="Startup Fundraising Platform - MVP")

# Configure Stripe (dummy for demonstration)
stripe.api_key = STRIPE_SECRET_KEY
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Domains allowed to make requests
    allow_credentials=True,         # Allow cookies and credentials
    allow_methods=["*"],            # HTTP methods allowed (e.g., GET, POST)
    allow_headers=["*"],            # Headers allowed in requests
)

#------------------------------------------------------
# Authentication
#------------------------
@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password, form_data.client_id)
    if not user:
        raise HTTPException(
            status_code=400,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user["email"]}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/signin")
async def signin(data: schema.SignInSchema, db: Session = Depends(get_db)):
    user_models = ["founder", "investor", "admin"]
    for u in user_models:
        if user:= auth.authenticate_user(email=data.email, password=data.password, user_type=u):
            return user
       
    raise HTTPException(status_code=401, detail="We couldn't log you in.")

# ------------------------------------------------------------------
#  Admin Functions
# ------------------------------------------------------------------
def create_admin(db: Session, email: str, password: str):
    admin = models.Admin(email=email, password=utils.hash_password(password))
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin

# ------------------------------------------------------------------
#  CRUD for Founder
# ------------------------------------------------------------------
@app.get("/founders", response_model=list[schema.FounderOut])
def read_founders(db: Session = Depends(get_db)):
    return db.query(models.Founder).all()

@app.get("/founders/{founder_id}", response_model=schema.FounderOut)
def read_founder(founder_id: int, db: Session = Depends(get_db)):
    founder = db.query(models.Founder).filter(models.Founder.id == founder_id).first()
    if not founder:
        raise HTTPException(status_code=404, detail="Founder not found")
    return founder

@app.post("/founders", response_model=schema.FounderOut, status_code=status.HTTP_201_CREATED)
def create_founder(founder_data: schema.FounderCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Founder).filter(models.Founder.email == founder_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Founder with this email already exists.")
    hashed_pw = utils.hash_password(founder_data.password)
    new_founder = models.Founder(
        name=founder_data.fullName,
        email=founder_data.email,
        password=hashed_pw,
        contact_details=founder_data.contact_details,
        role=founder_data.role,
        industry=founder_data.industry,
        companyName=founder_data.companyName
    )
    db.add(new_founder)
    db.commit()
    db.refresh(new_founder)
    return new_founder

@app.put("/founders/{founder_id}", response_model=schema.FounderOut)
def update_founder(founder_id: int, founder_data: schema.FounderUpdate, db: Session = Depends(get_db)):
    founder = db.query(models.Founder).filter(models.Founder.id == founder_id).first()
    if not founder:
        raise HTTPException(status_code=404, detail="Founder not found")

    if founder_data.name is not None:
        founder.name = founder_data.name
    if founder_data.email is not None:
        # Check for duplicate email
        if (db.query(models.Founder)
              .filter(models.Founder.email == founder_data.email, models.Founder.id != founder_id)
              .first()):
            raise HTTPException(status_code=400, detail="Email already in use.")
        founder.email = founder_data.email
    if founder_data.password is not None:
        founder.password = utils.hash_password(founder_data.password)
    if founder_data.contact_details is not None:
        founder.contact_details = founder_data.contact_details

    db.commit()
    db.refresh(founder)
    return founder

@app.delete("/founders/{founder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_founder(founder_id: int, db: Session = Depends(get_db)):
    founder = db.query(models.Founder).filter(models.Founder.id == founder_id).first()
    if not founder:
        raise HTTPException(status_code=404, detail="Founder not found")
    db.delete(founder)
    db.commit()
    return None

# ------------------------------------------------------------------
#  CRUD for Investor
# ------------------------------------------------------------------
@app.get("/investors", response_model=list[schema.InvestorOut])
def read_investors(db: Session = Depends(get_db)):
    return db.query(models.Investor).all()

@app.get("/investors/{investor_id}", response_model=schema.InvestorOut)
def read_investor(investor_id: int, db: Session = Depends(get_db)):
    investor = db.query(models.Investor).filter(models.Investor.id == investor_id).first()
    if not investor:
        raise HTTPException(status_code=404, detail="Investor not found")
    return investor

@app.post("/investors", response_model=schema.InvestorOut, status_code=status.HTTP_201_CREATED)
def create_investor(investor_data: schema.InvestorCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Investor).filter(models.Investor.email == investor_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Investor with this email already exists.")
    hashed_pw = utils.hash_password(investor_data.password)
    data = investor_data.model_dump()
    data.update({"role":"investor", "password":hashed_pw, "name": investor_data.fullName})
    data.pop("fullName")
    new_investor = models.Investor(
        **data,
        other_details=investor_data.model_dump_json()

    )
    db.add(new_investor)
    db.commit()
    db.refresh(new_investor)
    return new_investor

@app.put("/investors/{investor_id}", response_model=schema.InvestorOut)
def update_investor(investor_id: int, investor_data: schema.InvestorUpdate, db: Session = Depends(get_db)):
    investor = db.query(models.Investor).filter(models.Investor.id == investor_id).first()
    if not investor:
        raise HTTPException(status_code=404, detail="Investor not found")

    if investor_data.name is not None:
        investor.name = investor_data.name
    if investor_data.email is not None:
        # Check for duplicate email
        if (db.query(models.Investor)
              .filter(models.Investor.email == investor_data.email, models.Investor.id != investor_id)
              .first()):
            raise HTTPException(status_code=400, detail="Email already in use.")
        investor.email = investor_data.email
    if investor_data.password is not None:
        investor.password = utils.hash_password(investor_data.password)

    db.commit()
    db.refresh(investor)
    return investor

@app.delete("/investors/{investor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_investor(investor_id: int, db: Session = Depends(get_db)):
    investor = db.query(models.Investor).filter(models.Investor.id == investor_id).first()
    if not investor:
        raise HTTPException(status_code=404, detail="Investor not found")
    db.delete(investor)
    db.commit()
    return None

# ------------------------------------------------------------------
#  CRUD for Project
# ------------------------------------------------------------------
@app.get("/campaigns")
def get_projects(db: Session = Depends(get_db)):
    """List all projects (for feed)."""
    projects = db.query(models.Project).all()
    response_data = []
    for p in list(projects):
        response_data.append(p.get_dict())

    return response_data

@app.get("/campaigns/{project_id}")
def get_project_details(project_id: int, db: Session = Depends(get_db)):
    """Get project details by ID."""
    project = db.query(models.Project).filter(models.Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    response_obj = {
        "image_url": "/static/" + project.image_url.split("/")[-1],
        "proof_file_url": "/static/" + project.pdf_document_path.split("/")[-1],

    }
    response_data = project.get_dict()

    return response_data


@app.post("/campaigns", status_code=status.HTTP_201_CREATED)
def create_project(
    campaignTitle: str = Form(...),
    campaignDescription: str = Form(...),
    campaignCategory: str = Form(...),
    targetAmount: float = Form(...),
    fundingType: str = Form(...),
    deadline: str = Form(...),
    minInvestment: float = Form(...),
    email: str = Form(...),
    address: str = Form(...),
    phone: str = Form(...),
    personalizedMessage: str = Form(None),
    motivationLetter: str = Form(None),
    proofOfEligibility: UploadFile = File(...),
    campaignImage: UploadFile = File(...),
    founder_id: int = 1,  # Replace with authentication logic
    db: Session = Depends(get_db),
):
    """
    Create a new project with files and save them to the static directory.
    """

    # Validate static directory
    if not os.path.exists(STATIC_FILES_DIR):
        os.makedirs(STATIC_FILES_DIR)

    # Save the proof_of_eligibility file
    proof_file_path = os.path.join(
        STATIC_FILES_DIR, f"proof_{datetime.now().strftime('%Y%m%d%H%M%S')}_{proofOfEligibility.filename}"
    )
    with open(proof_file_path, "wb") as buffer:
        shutil.copyfileobj(proofOfEligibility.file, buffer)

    # Save the campaign_image file
    image_file_path = os.path.join(
        STATIC_FILES_DIR, f"image_{datetime.now().strftime('%Y%m%d%H%M%S')}_{campaignImage.filename}"
    )
    with open(image_file_path, "wb") as buffer:
        shutil.copyfileobj(campaignImage.file, buffer)

    # Create a new project instance
    new_project = models.Project(
        name=campaignTitle,
        description=campaignDescription,
        target_amount=targetAmount,
        image_url=image_file_path,
        pdf_document_path=proof_file_path,
        founder_id=founder_id,
        deadline=deadline,
        fundingType=fundingType,
        minInvestment=minInvestment,
        email=email,
        address=address,
        phone=phone,
        personalizedMessage=personalizedMessage,
        motivationLetter=motivationLetter,
        campaignCategory=campaignCategory,
        campaignTitle=campaignTitle,
        other_details=None,  # Set this to additional details if available
    )

    # Save the project to the database
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    


    return new_project.get_dict()


@app.put("/campaigns/{project_id}", response_model=schema.ProjectOut)
def update_project(
    project_id: int,
    project_data: schema.ProjectUpdate,
    db: Session = Depends(get_db)
):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project_data.name is not None:
        project.name = project_data.name
    if project_data.description is not None:
        project.description = project_data.description
    if project_data.target_amount is not None:
        project.target_amount = project_data.target_amount
    if project_data.image_url is not None:
        project.image_url = project_data.image_url
    if project_data.status is not None:
        project.status = project_data.status

    db.commit()
    db.refresh(project)
    return project

@app.delete("/campaigns/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()
    return None

@app.get("/campaigns/{project_id}/pdf", response_class=FileResponse)
def get_project_pdf(project_id: int, db: Session = Depends(get_db)):
    """
    Endpoint to download/view the PDF document for a project.
    """
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.pdf_document_path or not os.path.exists(project.pdf_document_path):
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(project.pdf_document_path, media_type='application/pdf')

# ------------------------------------------------------------------
#  CRUD for Investment
# ------------------------------------------------------------------
@app.get("/investments", response_model=list[schema.InvestmentOut])
def read_investments(investor_id: int | None = None, db: Session = Depends(get_db)):
    return db.query(models.Investment).filter(models.Investment.investor_id == investor_id).all()

@app.get("/investments/{investment_id}", response_model=schema.InvestmentOut)
def read_investment(investment_id: int, db: Session = Depends(get_db)):
    investment = db.query(models.Investment).filter(models.Investment.id == investment_id).first()
    if not investment:
        raise HTTPException(status_code=404, detail="Investment not found")
    return investment

@app.post("/investments", response_model=schema.InvestmentOut, status_code=status.HTTP_201_CREATED)
def create_investment(
    investment_data: schema.InvestmentCreate,
    investor_id: int = 1,  # from auth in real app
    db: Session = Depends(get_db)
):
    """
    Demonstration only. Full Stripe integration would handle PaymentIntents, etc.
    """
    project = db.query(models.Project).filter(models.Project.id == investment_data.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.fundsRaised = project.fundsRaised + investment_data.amount
    new_investment = models.Investment(
        amount=investment_data.amount,
        investor_id=investor_id,
        project_id=investment_data.project_id
    )
    db.add(new_investment)
    db.commit()
    db.refresh(new_investment)
    return new_investment

@app.put("/investments/{investment_id}", response_model=schema.InvestmentOut)
def update_investment(investment_id: int, investment_data: schema.InvestmentUpdate, db: Session = Depends(get_db)):
    investment = db.query(models.Investment).filter(models.Investment.id == investment_id).first()
    if not investment:
        raise HTTPException(status_code=404, detail="Investment not found")

    if investment_data.project_id is not None:
        # Check if project exists
        project = db.query(models.Project).filter(models.Project.id == investment_data.project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        investment.project_id = investment_data.project_id

    if investment_data.amount is not None:
        investment.amount = investment_data.amount

    db.commit()
    db.refresh(investment)
    return investment

@app.delete("/investments/{investment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_investment(investment_id: int, db: Session = Depends(get_db)):
    investment = db.query(models.Investment).filter(models.Investment.id == investment_id).first()
    if not investment:
        raise HTTPException(status_code=404, detail="Investment not found")
    db.delete(investment)
    db.commit()
    return None

@app.get("/investor/investments", response_model=list[schema.InvestmentOut])
def get_investor_investments(investor_id: int = 1, db: Session = Depends(get_db)):
    """Retrieve all startups the investor has invested in."""
    investments = db.query(models.Investment).filter(models.Investment.investor_id == investor_id).all()
    return investments

# ------------------------------------------------------------------
#  CRUD for Project Updates
# ------------------------------------------------------------------
@app.get("/updates", response_model=list[schema.UpdateOut])
def read_updates(db: Session = Depends(get_db)):
    return db.query(models.Update).all()

@app.get("/updates/{update_id}", response_model=schema.UpdateOut)
def read_update(update_id: int, db: Session = Depends(get_db)):
    update = db.query(models.Update).filter(models.Update.id == update_id).first()
    if not update:
        raise HTTPException(status_code=404, detail="Update not found")
    return update

@app.post("/updates", response_model=schema.UpdateOut, status_code=status.HTTP_201_CREATED)
def create_project_update(
    update_data: schema.UpdateCreate,
    founder_id: int = 1,  # from auth in real app
    db: Session = Depends(get_db)
):
    project = db.query(models.Project).filter(models.Project.id == update_data.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    if project.founder_id != founder_id:
        raise HTTPException(status_code=403, detail="Not the project founder.")

    new_update = models.Update(
        content=update_data.content,
        project_id=update_data.project_id
    )
    db.add(new_update)
    db.commit()
    db.refresh(new_update)
    return new_update

@app.put("/updates/{update_id}", response_model=schema.UpdateOut)
def update_project_update(
    update_id: int,
    update_data: schema.UpdateUpdate,
    founder_id: int = 1,  # from auth
    db: Session = Depends(get_db)
):
    existing_update = db.query(models.Update).filter(models.Update.id == update_id).first()
    if not existing_update:
        raise HTTPException(status_code=404, detail="Update not found")

    # Must be the project's founder to edit
    project = db.query(models.Project).filter(models.Project.id == existing_update.project_id).first()
    if project.founder_id != founder_id:
        raise HTTPException(status_code=403, detail="Not the project founder.")

    if update_data.content is not None:
        existing_update.content = update_data.content

    db.commit()
    db.refresh(existing_update)
    return existing_update

@app.delete("/updates/{update_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_update(
    update_id: int,
    founder_id: int = 1,  # from auth
    db: Session = Depends(get_db)
):
    existing_update = db.query(models.Update).filter(models.Update.id == update_id).first()
    if not existing_update:
        raise HTTPException(status_code=404, detail="Update not found")

    project = db.query(models.Project).filter(models.Project.id == existing_update.project_id).first()
    if project.founder_id != founder_id:
        raise HTTPException(status_code=403, detail="Not the project founder.")

    db.delete(existing_update)
    db.commit()
    return None

@app.get("/project/{project_id}/updates", response_model=list[schema.UpdateOut])
def get_project_updates(project_id: int, investor_id: int = 1, db: Session = Depends(get_db)):
    """Investors who have invested in that project can see updates."""
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if investor has invested
    investment = db.query(models.Investment).filter(
        models.Investment.project_id == project_id,
        models.Investment.investor_id == investor_id
    ).first()
    if not investment:
        raise HTTPException(status_code=403, detail="You have not invested in this project.")
    
    updates = db.query(models.Update).filter(models.Update.project_id == project_id).all()
    return updates

# ------------------------------------------------------------------
#  CRUD for Admin
# ------------------------------------------------------------------
@app.get("/admins", response_model=list[schema.AdminOut])
def read_admins(db: Session = Depends(get_db)):
    return db.query(models.Admin).all()

@app.get("/admins/{admin_id}", response_model=schema.AdminOut)
def read_admin(admin_id: int, db: Session = Depends(get_db)):
    admin = db.query(models.Admin).filter(models.Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    return admin

@app.post("/admins", response_model=schema.AdminOut)
def register_admin(admin_data: schema.AdminCreate, token: str, db: Session = Depends(get_db)):
    """Protected endpoint requiring a token from .env to create a platform admin."""
    if token != ADMIN_CREATION_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid admin creation token")
    existing = db.query(models.Admin).filter(models.Admin.email == admin_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Admin with this email already exists.")

    admin = create_admin(db, admin_data.email, admin_data.password)
    return admin

@app.put("/admins/{admin_id}", response_model=schema.AdminOut)
def update_admin(admin_id: int, admin_data: schema.AdminUpdate, db: Session = Depends(get_db)):
    admin = db.query(models.Admin).filter(models.Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    if admin_data.email is not None:
        # Check for duplicate
        if (db.query(models.Admin)
                .filter(models.Admin.email == admin_data.email, models.Admin.id != admin_id)
                .first()):
            raise HTTPException(status_code=400, detail="Email already in use by another admin.")
        admin.email = admin_data.email
    if admin_data.password is not None:
        admin.password = utils.hash_password(admin_data.password)

    db.commit()
    db.refresh(admin)
    return admin

@app.delete("/admins/{admin_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin(admin_id: int, db: Session = Depends(get_db)):
    admin = db.query(models.Admin).filter(models.Admin.id == admin_id).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    db.delete(admin)
    db.commit()
    return None


app.mount("/static", StaticFiles(directory=STATIC_FILES_DIR), name="static")
