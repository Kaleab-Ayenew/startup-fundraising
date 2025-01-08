from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from .database import Base

class Founder(Base):
    __tablename__ = 'founders'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    contact_details = Column(String, nullable=True)
    companyName = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    role = Column(String, nullable=True)
    other_details = Column(Text, nullable=True)

    projects = relationship("Project", back_populates="founder")

class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    target_amount = Column(Float, default=0.0)
    image_url = Column(String, nullable=True)
    pdf_document_path = Column(String, nullable=True)
    founder_id = Column(Integer, ForeignKey("founders.id"), nullable=False)
    deadline = Column(DateTime)
    fundingType = Column(String)
    minInvestment = Column(Integer)
    email = Column(String)
    address = Column(String)
    phone = Column(String)
    personalizedMessage = Column(String)
    motivationLetter = Column(String)
    campaignCategory = Column(String)
    campaignDescription = Column(String)
    campaignTitle = Column(String)
    status = Column(String, default="pending", nullable=True)
    other_details = Column(Text, nullable=True)



    founder = relationship("Founder", back_populates="projects")
    investors = relationship("Investment", back_populates="project")
    updates = relationship("Update", back_populates="project")

class Investor(Base):
    __tablename__ = 'investors'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    investmentFocus = Column(String, nullable=True)
    investmentBudget = Column(String, nullable=True)
    investmetSector = Column(String, nullable=True)
    investmentExperience = Column(String, nullable=True)
    linkedInProfile = Column(String, nullable=True)
    role = Column(String, nullable=True)
    other_details = Column(Text, nullable=True)

    investments = relationship("Investment", back_populates="investor")

class Investment(Base):
    __tablename__ = 'investments'
    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    investor_id = Column(Integer, ForeignKey("investors.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    other_details = Column(Text, nullable=True)

    investor = relationship("Investor", back_populates="investments")
    project = relationship("Project", back_populates="investors")

class Update(Base):
    __tablename__ = 'updates'
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    other_details = Column(Text, nullable=True)

    project = relationship("Project", back_populates="updates")

class Admin(Base):
    __tablename__ = 'admins'
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    other_details = Column(Text, nullable=True)
