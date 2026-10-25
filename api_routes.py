import re
from fastapi import APIRouter, status
from fastapi.responses import FileResponse, JSONResponse
from schemas import PassportRequest, PassportResponse
from calc_engine import calculate_deposit, GeometryError
from doc_builder import build_passport, resolve_passport_path, get_deposit_name, DocumentBuildError

router = APIRouter()


@router.post("/generate-passport", response_model=PassportResponse, status_code=status.HTTP_200_OK)
def generate_passport(request: PassportRequest):
    try:
        payload = request.model_dump()
        calc_result = calculate_deposit(payload)
        file_id = build_passport(calc_result)
    except GeometryError as exc:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "status": "error",
                "message": str(exc),
                "errors": [{"field": "contour", "problem": str(exc)}],
            },
        )
    except DocumentBuildError:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "message": "Внутренняя ошибка сервера при формировании документа",
            },
        )

    summary = {
        "area_m2": calc_result["area_m2"],
        "area_ha": calc_result["area_ha"],
        "thickness_weighted_m": calc_result["thickness_weighted_m"],
        "thickness_arithmetic_m": calc_result["thickness_arithmetic_m"],
        "volume_m3": calc_result["volume_m3"],
        "reserves_t": calc_result["reserves_t"],
        "reserves_kt": calc_result["reserves_kt"],
        "reserves_category": calc_result["reserves_category"],
        "boreholes_outside_contour": calc_result["boreholes_outside_contour"],
        "corner_points_count": len(calc_result.get("corner_points", [])),
    }
    if calc_result.get("weighting_method") == "voronoi":
        summary["weighting_method"] = "voronoi"
        summary["weighting_fallback"] = calc_result.get("weighting_fallback", False)
    if calc_result.get("reserves_balance_warning"):
        summary["reserves_balance_warning"] = calc_result["reserves_balance_warning"]

    return PassportResponse(
        status="ok",
        file_id=file_id,
        download_url=f"/download/{file_id}",
        summary=summary,
    )


@router.get("/download/{file_id}")
def download_passport(file_id: str):
    path = resolve_passport_path(file_id)
    if path is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"status": "error", "message": "Файл не найден"},
        )
    deposit_name = get_deposit_name(file_id)
    if deposit_name:
        clean_name = re.sub(r'[\\/*?:"<>|\x00-\x1f]', "_", deposit_name).strip()
        filename = f"Passport_N_{clean_name}.docx"
    else:
        filename = f"Passport_N_{file_id}.docx"

    return FileResponse(
        path=str(path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )


@router.get("/health")
def health_check():
    return {"status": "ok"}
