from typing import Any, Literal
from typing_extensions import Self
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PointModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: float = Field(allow_inf_nan=False)
    y: float = Field(allow_inf_nan=False)


class BoreholeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    borehole_id: str
    x: float = Field(allow_inf_nan=False)
    y: float = Field(allow_inf_nan=False)
    thickness_m: float = Field(gt=0, le=500, allow_inf_nan=False)
    weight: float = Field(default=1.0, gt=0, allow_inf_nan=False)

    @field_validator("borehole_id", mode="before")
    @classmethod
    def validate_borehole_id(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError("Идентификатор скважины должен быть строкой")
        v = v.strip()
        if not v:
            raise ValueError("Идентификатор скважины не должен быть пустым")
        return v


class QualityModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    modulus_fineness: float = Field(gt=0, le=6, allow_inf_nan=False)
    clay_content_pct: float = Field(ge=0, le=100, allow_inf_nan=False)
    moisture_pct: float = Field(ge=0, le=100, allow_inf_nan=False)
    bulk_density_t_m3: float = Field(ge=0.5, le=3.0, allow_inf_nan=False)


class PassportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_name: str
    deposit_name: str
    license_number: str
    mineral_type: str = "Песок строительный"
    region: str
    coordinate_system: Literal["local_metric", "geographic"] = "local_metric"
    contour: list[PointModel] = Field(min_length=3)
    boreholes: list[BoreholeModel] = Field(min_length=1)
    quality: QualityModel
    density_t_m3: float = Field(ge=0.5, le=3.0, allow_inf_nan=False)
    declared_area_ha: float | None = Field(default=None, ge=0, allow_inf_nan=False)

    @field_validator("company_name", "deposit_name", "license_number", "mineral_type", "region", mode="before")
    @classmethod
    def validate_non_empty_strings(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError("Поле должно быть строкой")
        v = v.strip()
        if not v:
            raise ValueError("Текстовое поле не может быть пустым")
        return v

    @field_validator("contour")
    @classmethod
    def validate_contour(cls, v: list[PointModel]) -> list[PointModel]:
        if len(v) < 3:
            raise ValueError("Контур должен содержать минимум 3 вершины")
        unique_points = {(p.x, p.y) for p in v}
        if len(unique_points) < 3:
            raise ValueError("Контур должен содержать минимум 3 различные вершины")
        return v

    @field_validator("boreholes")
    @classmethod
    def validate_boreholes(cls, v: list[BoreholeModel]) -> list[BoreholeModel]:
        if len(v) < 1:
            raise ValueError("Должна быть передана хотя бы одна скважина")
        ids = [b.borehole_id for b in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Идентификаторы скважин должны быть уникальными")
        return v

    @model_validator(mode="after")
    def validate_coordinates(self) -> Self:
        if self.coordinate_system == "geographic":
            for idx, pt in enumerate(self.contour):
                if not (-180.0 <= pt.x <= 180.0):
                    raise ValueError(f"Долгота точки контура {idx} должна быть в диапазоне [-180, 180]")
                if not (-90.0 <= pt.y <= 90.0):
                    raise ValueError(f"Широта точки контура {idx} должна быть в диапазоне [-90, 90]")
            for bh in self.boreholes:
                if not (-180.0 <= bh.x <= 180.0):
                    raise ValueError(f"Долгота скважины {bh.borehole_id} должна быть в диапазоне [-180, 180]")
                if not (-90.0 <= bh.y <= 90.0):
                    raise ValueError(f"Широта скважины {bh.borehole_id} должна быть в диапазоне [-90, 90]")
        return self


class PassportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    file_id: str
    download_url: str
    summary: dict[str, Any]
