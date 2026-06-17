import logo from "@/resources/images/logo.png";
import menuIcon from "@/resources/images/menu-icon.svg";
import closeIcon from "@/resources/images/close-icon.svg";
import "rsuite/Button/styles/index.css";
import "rsuite/Col/styles/index.css";
import "rsuite/Row/styles/index.css";
import "@/resources/scss/sidebar_style.scss";
import { ROUTES } from "@/constants";
import { logout, getUserName, isAuth } from "@/services/Auth";
import { useEffect, useState, FormEvent } from "react";
import { NavLink } from "react-router-dom";
import { Col, Row } from "rsuite";


export default function Sidebar() {
    const [ currentUser, setCurrentUser ] = useState(getUserName);
    const [ show, setShow ] = useState(false);

    useEffect(() => {
        if (isAuth())
            setCurrentUser(getUserName());
    }, []);

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        await logout();
        setCurrentUser(null);
    };


    return (
        <div className={ show ? "sidebar show" : "sidebar" }>
            <div id="navToggler" onClick={ () => setShow(!show) }>
                <img src={ show ? closeIcon : menuIcon } width="30" alt="Toggle Sidebar" />
            </div>

            <div className="logo-wrapper"><img src={ logo } alt="Логотип" className="logo" /></div>

            <div className="mobile-space"></div>

            <div className="nav-block">
                <NavLink to={ ROUTES.DASHBOARD } className="nav-btn">Панель инструментов</NavLink>
                <div className="nav-btn disabled">Управление маршрутами</div>
                <div className="nav-btn disabled">Управление точками</div>
                <NavLink to={ ROUTES.DATA_IMPORT } className="nav-btn">Загрузка данных</NavLink>
                <NavLink to={ ROUTES.DEMO_GUESTS } className="nav-btn">Демо-ссылки</NavLink>
                <NavLink to={ ROUTES.RATES_MANAGEMENT } className="nav-btn">Курсы валют</NavLink>
            </div>

            <div>
                <Row className="authentication-block">
                    <Col><div className="nav-btn">{ currentUser }</div></Col>
                    <Col><button onClick={ handleSubmit } className="nav-btn">Выйти</button></Col>
                </Row>

                <div className="back_to_site-wrapper">
                    <button onClick={ () => {
                        history.pushState([], "", ROUTES.MAIN_SITE);
                        location.reload();
                    } } className="nav-btn">Вернуться на сайт</button>
                </div>
            </div>
        </div>
    );
}
