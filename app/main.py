import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ValidationError
from sqlalchemy import Column, Float, Integer, String, create_engine, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from typing import List, Optional, Union
from sqlalchemy.orm import declarative_base, relationship, joinedload
from sqlalchemy.orm import sessionmaker
import os
from pydantic import UUID4
#
# engine = create_engine('postgresql://postgres:1234@localhost:5432/postgres')
# Base = declarative_base()
# Session = sessionmaker(bind=engine)
# session = Session()


POSTGRES_USER = os.environ.get('POSTGRES_USER')
POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD')
POSTGRES_HOST = 'db'
POSTGRES_PORT = '5432'
POSTGRES_DB = os.environ.get('POSTGRES_DB')

# Строка подключения к базе данных
DATABASE_URL = f'postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}'

engine = create_engine(DATABASE_URL)

Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()


class MenuModel(Base):
    __tablename__ = 'menus'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    title = Column(String)
    submenus_count = Column(Integer, default=0)
    dishes_count = Column(Integer, default=0)
    description = Column(String)
    submenus = relationship("SubmenuModel", back_populates="menu")


class SubmenuModel(Base):
    __tablename__ = 'submenus'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    title = Column(String)
    description = Column(String)
    dishes_count = Column(Integer, default=0)
    menu_id = Column(UUID(as_uuid=True), ForeignKey("menus.id"))
    menu = relationship("MenuModel", back_populates="submenus")
    dishes = relationship("DishModel", back_populates="submenu")


class DishModel(Base):
    __tablename__ = 'dishes'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    title = Column(String)
    description = Column(String)
    price = Column(String)
    submenu_id = Column(UUID(as_uuid=True), ForeignKey("submenus.id"))
    submenu = relationship("SubmenuModel", back_populates="dishes")


Base.metadata.create_all(bind=engine)


class Dish(BaseModel):
    title: str
    description: str
    price: str


class Submenu(BaseModel):
    title: str
    description: str
    dishes: Optional[list[Dish]] = []
    dishes_count: int = 0


class Menu(BaseModel):
    title: str
    description: str
    submenus: Optional[list[Submenu]] = []
    dishes_count: int = 0
    submenus_count: int = 0


class MenuUpdate(BaseModel):
    title: Optional[str]
    description: Optional[str]


class UpdatedMenu(BaseModel):
    id: UUID4
    title: str
    description: str


class SubmenuUpdate(BaseModel):
    title: Optional[str]
    description: Optional[str]


class DishUpdate(BaseModel):
    title: Optional[str]
    description: Optional[str]
    price: Optional[str]


app = FastAPI()


@app.post("/api/v1/menus", status_code=201)
async def create_menu(menu: Menu):
    db_menu = MenuModel(title=menu.title, description=menu.description, submenus=menu.submenus)
    session.add(db_menu)
    session.commit()

    return {"id": db_menu.id, "title": db_menu.title, "description": db_menu.description,
            "submenus_count": menu.submenus_count, "dishes_count": menu.dishes_count}


@app.get("/api/v1/get_submenu/{submenu_id}")
def read_submenus(submenu_id: uuid.UUID):
    db_submenu = session.query(SubmenuModel).filter(SubmenuModel.id == submenu_id).first()
    if db_submenu:
        submenu_info = {"submenu_id": db_submenu.id, "tittle": db_submenu.title, "description": db_submenu.description,
                        "dishes_count": db_submenu.dishes_count}
        dishes_info = [{"title": dish.title, "description": dish.description, "price": dish.price} for dish in
                       db_submenu.dishes]
        submenu_info["dishes"] = dishes_info
        return submenu_info
    else:
        return {"message": "Submenu not found"}


@app.get("/api/v1/menus")
def print_all_menus():
    all_menus = session.query(MenuModel).all()
    menus_info = []
    for menu in all_menus:
        submenu_info = [{"id": submenu.id, "title": submenu.title, "description": submenu.description} for submenu in
                        menu.submenus]
        menus_info.append(
            {"id": menu.id, "title": menu.title, "description": menu.description, "submenus": submenu_info,
             "submenus_count": menu.submenus_count, "dishes_count": menu.dishes_count})
    return menus_info


@app.get("/api/v1/menus/{target_menu_id}")
def read_menu(target_menu_id: uuid.UUID):
    db_menu = session.query(MenuModel).filter(MenuModel.id == target_menu_id).first()
    if db_menu == None:
        raise HTTPException(status_code=404, detail="menu not found")
    else:
        menu_info = {"id": target_menu_id, "title": db_menu.title, "description": db_menu.description,
                     "submenus_count": db_menu.submenus_count, "dishes_count": db_menu.dishes_count}
        if db_menu.submenus:
            submenus_info = [read_submenus(submenu.id) for submenu in db_menu.submenus]
            menu_info["submenus"] = submenus_info
        else:
            menu_info["submenus"] = []
        return menu_info


@app.patch("/api/v1/menus/{target_menu_id}", response_model=UpdatedMenu)
def update_menu(target_menu_id: uuid.UUID, menu: MenuUpdate):
    if target_menu_id is None:
        raise HTTPException(status_code=400, detail="Invalid target_menu_id")

    db_menu = session.query(MenuModel).filter(MenuModel.id == target_menu_id).first()
    if db_menu is not None:
        if menu and menu.title:
            db_menu.title = menu.title
        if menu and menu.description:
            db_menu.description = menu.description
        session.commit()
        session.refresh(db_menu)
        return UpdatedMenu(
            id=str(db_menu.id),
            title=db_menu.title,
            description=db_menu.description
        )
    else:
        raise HTTPException(status_code=404, detail="Menu not found")


@app.delete("/api/v1/menus/{target_menu_id}")
def delete_menu(target_menu_id: uuid.UUID):
    db_menu = session.query(MenuModel).filter(MenuModel.id == target_menu_id).first()
    if db_menu:
        submenus_to_remove = db_menu.submenus_count
        dishes_to_remove = db_menu.dishes_count
        for submenu in db_menu.submenus:
            dishes_to_remove += submenu.dishes_count
            session.delete(submenu)
        session.delete(db_menu)
        session.commit()
        db_menu.submenus_count -= submenus_to_remove
        db_menu.dishes_count -= dishes_to_remove
        session.commit()
        return {"message": "correct delete"}
    return {"message": "menu dont found"}


@app.get("/api/v1/menus/{api_test_menu_id}/submenus")
def show_submenus(api_test_menu_id: uuid.UUID):
    menu = session.query(MenuModel).filter(MenuModel.id == api_test_menu_id).first()
    if menu is None:
        return []
    submenu_info = []
    for submenu in menu.submenus:
        submenu_dishes = []
        for dish in submenu.dishes:
            submenu_dishes.append(
                {"id": dish.id, "title": dish.title, "description": dish.description, "price": dish.price})
        submenu_info.append({
            "id": submenu.id,
            "title": submenu.title,
            "description": submenu.description,
            "dishes": submenu_dishes,
            "dishes_count": submenu.dishes_count
        })
    return submenu_info


@app.post("/api/v1/menus/{api_test_menu_id}/submenus", status_code=201)
def create_submenu(api_test_menu_id: uuid.UUID, submenu: Submenu):
    nw_submenu = SubmenuModel(title=submenu.title, description=submenu.description)
    db_menu = session.query(MenuModel).filter(MenuModel.id == api_test_menu_id).first()
    if db_menu is None:
        return []
    for existing_submenu in db_menu.submenus:
        if existing_submenu.title == nw_submenu.title:
            raise HTTPException(status_code=400, detail="Submenu with the same title already exists in this menu")
    db_menu.submenus.append(nw_submenu)
    db_menu.submenus_count += 1
    session.add(nw_submenu)
    session.commit()
    return {"id": nw_submenu.id, "title": nw_submenu.title,
            "description": nw_submenu.description,
            "dishes_count": submenu.dishes_count}


@app.get("/api/v1/menus/{api_test_menu_id}/submenus/{submenu_id}")
def show_submenu(api_test_menu_id: uuid.UUID, submenu_id: uuid.UUID):
    menu = session.query(MenuModel).filter(MenuModel.id == api_test_menu_id).first()
    for a in menu.submenus:
        if a.id == submenu_id:
            submenu_info = {"id": a.id, "title": a.title, "description": a.description, "dishes_count": a.dishes_count}
            dishes_info = [{"id": dish.id, "title": dish.title, "description": dish.description,
                            "price": "{:.2f}".format(round(float(dish.price), 2))} for dish in a.dishes]
            submenu_info["dishes"] = dishes_info
            return submenu_info
    raise HTTPException(status_code=404, detail="submenu not found")


@app.patch("/api/v1/menus/{api_test_menu_id}/submenus/{submenu_id}")
def update_submenu(api_test_menu_id: uuid.UUID, submenu_id: uuid.UUID, submenu: SubmenuUpdate):
    menu = session.query(MenuModel).filter(MenuModel.id == api_test_menu_id).first()
    if menu is not None:
        for a in menu.submenus:
            if a.id == submenu_id:
                if submenu.title:
                    for existing_submenu in menu.submenus:
                        if existing_submenu.id != submenu_id and existing_submenu.title == submenu.title:
                            raise HTTPException(status_code=400,
                                                detail="Submenu with the same title already exists in this menu")
                    a.title = submenu.title
                if submenu.description:
                    a.description = submenu.description
                session.commit()
                session.refresh(a)
                return {"id": a.id, "title": a.title, "description": a.description, "dishes_count": a.dishes_count}
        raise HTTPException(status_code=404, detail="Submenu not found")
    raise HTTPException(status_code=404, detail="Menu not found")


@app.delete("/api/v1/menus/{api_test_menu_id}/submenus/{submenu_id}")
def delete_submenu(api_test_menu_id: uuid.UUID, submenu_id: uuid.UUID):
    menu = session.query(MenuModel).filter(MenuModel.id == api_test_menu_id).first()
    il = 0
    for i, submenu in enumerate(menu.submenus):
        if submenu.id == submenu_id:
            for dish in submenu.dishes:
                session.delete(dish)
                submenu.dishes_count -= 1
                il += 1

            session.delete(submenu)
            session.commit()
            menu.submenus_count -= 1
            menu.dishes_count -= il
            return {"message": "successful delete"}
    raise HTTPException(status_code=404, detail="submenu not found")


@app.get("/api/v1/menus/{api_test_menu_id}/submenus/{submenu_id}/dishes")
def show_dishes(api_test_menu_id: uuid.UUID, submenu_id: uuid.UUID):
    menu = session.query(SubmenuModel).filter(
        SubmenuModel.id == submenu_id and SubmenuModel.menu_id == api_test_menu_id).first()
    if menu is None:
        return []
    dishes_info = []
    for dish in menu.dishes:
        dishes_info.append({"id": dish.id, "title": dish.title, "description": dish.description,
                            "price": "{:.2f}".format(round(float(dish.price), 2))})
    return dishes_info


@app.post("/api/v1/menus/{api_test_menu_id}/submenus/{submenu_id}/dishes", status_code=201)
def new_dish(api_test_menu_id: uuid.UUID, submenu_id: uuid.UUID, dish: Dish):
    nw_dish = DishModel(title=dish.title, description=dish.description, price=dish.price)
    submenu = session.query(SubmenuModel).filter(
        SubmenuModel.id == submenu_id and SubmenuModel.menu_id == api_test_menu_id).first()
    if submenu is None:
        raise HTTPException(status_code=404, detail="Submenu not found")
    for existing_dish in submenu.dishes:
        if existing_dish.title == dish.title:
            raise HTTPException(status_code=400, detail="Dish with the same name already exists in this submenu")
    submenu.dishes.append(nw_dish)
    submenu.dishes_count += 1
    menu = session.query(MenuModel).filter(MenuModel.id == api_test_menu_id).first()
    menu.dishes_count += 1
    session.add(nw_dish)
    session.commit()
    return {"id": nw_dish.id, "title": nw_dish.title, "description": nw_dish.description,
            "price": "{:.2f}".format(round(float(nw_dish.price), 2))}


@app.get("/api/v1/menus/{api_test_menu_id}/submenus/{submenu_id}/dishes/{dish_id}")
def show_dish(api_test_menu_id: uuid.UUID, submenu_id: uuid.UUID, dish_id: uuid.UUID):
    submenu = session.query(SubmenuModel).filter(
        SubmenuModel.id == submenu_id and SubmenuModel.menu_id == api_test_menu_id).first()
    for a in submenu.dishes:
        if a.id == dish_id:
            return {"id": a.id, "title": a.title, "description": a.description, "price": "{:.2f}".format(round(float(a.price), 2))}
    raise HTTPException(status_code=404, detail="dish not found")


@app.patch("/api/v1/menus/{api_test_menu_id}/submenus/{submenu_id}/dishes/{dish_id}")
def update_dish(api_test_menu_id: uuid.UUID, submenu_id: uuid.UUID, dish_id: uuid.UUID, dish: DishUpdate):
    submenu = session.query(SubmenuModel).filter(
        SubmenuModel.id == submenu_id and SubmenuModel.menu_id == api_test_menu_id).first()
    if submenu is not None:
        for a in submenu.dishes:
            if a.id == dish_id:
                if dish.title:
                    for existing_dish in submenu.dishes:
                        if existing_dish.id != dish_id and existing_dish.title == dish.title:
                            raise HTTPException(status_code=400,
                                                detail="Dish with the same title already exists in this submenu")
                    a.title = dish.title
                if dish.description:
                    a.description = dish.description
                if dish.price:
                    a.price = "{:.2f}".format(round(float(dish.price), 2))
                session.commit()
                session.refresh(a)
                return {"id": a.id, "title": a.title, "description": a.description,
                        "price": "{:.2f}".format(round(float(a.price), 2))}
        raise HTTPException(status_code=404, detail="Dish not found")
    raise HTTPException(status_code=404, detail="Submenu not found")


@app.delete("/api/v1/menus/{api_test_menu_id}/submenus/{submenu_id}/dishes/{dish_id}")
def delete_dish(api_test_menu_id: uuid.UUID, submenu_id: uuid.UUID, dish_id: uuid.UUID):
    submenu = session.query(SubmenuModel).filter(
        SubmenuModel.id == submenu_id and SubmenuModel.menu_id == api_test_menu_id).first()
    for a in submenu.dishes:
        if a.id == dish_id:
            session.delete(a)
            session.commit()
            submenu.dishes_count += 1
            session.query(MenuModel).filter(MenuModel.id == api_test_menu_id).first().dishes_count += 1
            return {"message": "dish was deleted successful"}
    raise HTTPException(status_code=404, detail="dish not found")

