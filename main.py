from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import uvicorn
from api_routes import router

app = FastAPI(title="GeoSaaS API", version="0.1.0")

ERROR_TRANSLATIONS = {
    "missing": "Обязательное поле отсутствует",
    "string_too_short": "Длина строки меньше допустимой",
    "too_short": "Количество элементов меньше допустимого",
    "greater_than": "Значение должно быть больше допустимого",
    "greater_than_equal": "Значение должно быть больше или равно допустимому",
    "less_than": "Значение должно быть меньше допустимого",
    "less_than_equal": "Значение должно быть меньше или равно допустимому",
    "float_parsing": "Значение должно быть числом",
    "float_type": "Значение должно быть числом",
    "int_parsing": "Значение должно быть целым числом",
    "extra_forbidden": "Недопустимое дополнительное поле",
    "string_type": "Значение должно быть строкой",
    "finite_number": "Значение должно быть конечным числом",
    "json_invalid": "Тело запроса не является корректным JSON",
}


def format_error_item(err: dict) -> tuple[str, str]:
    loc_parts = [str(x) for x in err.get("loc", ())]
    if loc_parts and loc_parts[0] == "body":
        loc_parts = loc_parts[1:]
    field = ".".join(loc_parts) if loc_parts else "body"

    err_type = err.get("type", "")
    msg = str(err.get("msg", ""))

    if err_type == "missing":
        problem = "Обязательное поле отсутствует"
    elif err_type == "extra_forbidden":
        problem = "Недопустимое дополнительное поле"
    elif field.endswith("thickness_m") and err_type == "greater_than":
        problem = "Мощность должна быть больше 0"
    elif field == "contour" and (err_type == "too_short" or "3" in msg):
        problem = "Контур должен содержать минимум 3 вершины"
    elif msg.startswith("Value error, "):
        problem = msg[len("Value error, "):].strip()
    elif err_type in ERROR_TRANSLATIONS:
        problem = ERROR_TRANSLATIONS[err_type]
    else:
        problem = msg

    return field, problem


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    raw_errors = exc.errors()
    is_json_invalid = any(e.get("type") == "json_invalid" for e in raw_errors)
    if is_json_invalid:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "status": "error",
                "message": "Тело запроса не является корректным JSON",
                "errors": [
                    {"field": "body", "problem": "Тело запроса не является корректным JSON"}
                ],
            },
        )

    errors_list = []
    for err in raw_errors:
        field, problem = format_error_item(err)
        errors_list.append({"field": field, "problem": problem})

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "error",
            "message": "Входные данные не прошли проверку",
            "errors": errors_list,
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": str(exc.detail),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "message": "Внутренняя ошибка сервера",
        },
    )


app.include_router(router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
