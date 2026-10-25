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


class GeoPointModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lat: float = Field(ge=-90.0, le=90.0, allow_inf_nan=False)
    lon: float = Field(ge=-180.0, le=180.0, allow_inf_nan=False)


class StorageModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    length_m: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    width_m: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    height_m: float | None = Field(default=None, ge=0, allow_inf_nan=False)


class ChemicalOxideModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    value_pct: float = Field(ge=0, le=100, allow_inf_nan=False)

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError("Наименование окисла должно быть строкой")
        v = v.strip()
        if not v:
            raise ValueError("Наименование окисла не может быть пустым")
        return v


class ExtraCharacteristicModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str

    @field_validator("name", "description", mode="before")
    @classmethod
    def validate_str_fields(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError("Поле должно быть строкой")
        v = v.strip()
        if not v:
            raise ValueError("Поле не может быть пустым")
        return v


class CompositionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mineral: str | None = None
    chemical_oxides: list[ChemicalOxideModel] | None = None
    petrographic: str | None = None
    granulometric: str | None = None
    physico_mechanical: str | None = None

    @field_validator("mineral", "petrographic", "granulometric", "physico_mechanical", mode="before")
    @classmethod
    def strip_opt_str(cls, v: Any) -> str | None:
        if v is None:
            return None
        if isinstance(v, str):
            v_s = v.strip()
            return v_s if v_s else None
        return v


class ApplicationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mineral: str | None = None
    usage: str | None = None
    standard: str | None = None

    @field_validator("mineral", "usage", "standard", mode="before")
    @classmethod
    def strip_opt_str(cls, v: Any) -> str | None:
        if v is None:
            return None
        if isinstance(v, str):
            v_s = v.strip()
            return v_s if v_s else None
        return v


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

    confidentiality_stamp: str | None = None
    copy_number: str | None = None
    territorial_passport_number: str | None = None
    authority_passport_number: str | None = None
    compiler_name: str | None = None
    checker_name: str | None = None
    passport_date: str | None = None

    contract_info: str | None = None
    legal_address: str | None = None
    phone: str | None = None

    parent_deposit_name: str | None = None
    mining_method: str | None = None

    oblast: str | None = None
    district: str | None = None
    locality: str | None = None

    storage: StorageModel | None = None
    reserves_methodology: str | None = None
    composition: CompositionModel | None = None
    extra_characteristics: list[ExtraCharacteristicModel] | None = None
    applications: list[ApplicationModel] | None = None

    rock_origin: Literal["sedimentary", "metamorphic", "magmatic"] | None = None
    unit: str = "тыс. т"
    previous_passport_number: str | None = None
    previous_reserves_t: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    reserves_increment_t: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    reserves_realized_t: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    corner_points_geo: list[GeoPointModel] | None = None

    @field_validator("company_name", "deposit_name", "license_number", "mineral_type", "region", mode="before")
    @classmethod
    def validate_non_empty_strings(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError("Поле должно быть строкой")
        v = v.strip()
        if not v:
            raise ValueError("Текстовое поле не может быть пустым")
        return v

    @field_validator(
        "confidentiality_stamp",
        "copy_number",
        "territorial_passport_number",
        "authority_passport_number",
        "compiler_name",
        "checker_name",
        "passport_date",
        "contract_info",
        "legal_address",
        "phone",
        "parent_deposit_name",
        "mining_method",
        "oblast",
        "district",
        "locality",
        "reserves_methodology",
        "previous_passport_number",
        mode="before",
    )
    @classmethod
    def strip_optional_string(cls, v: Any) -> str | None:
        if v is None:
            return None
        if isinstance(v, str):
            v_stripped = v.strip()
            return v_stripped if v_stripped else None
        return v

    @field_validator("unit", mode="before")
    @classmethod
    def validate_unit(cls, v: Any) -> str:
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped:
                return v_stripped
        return "тыс. т"

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

    @field_validator("corner_points_geo")
    @classmethod
    def validate_corner_points_geo(cls, v: list[GeoPointModel] | None) -> list[GeoPointModel] | None:
        if v is not None:
            if len(v) < 3:
                raise ValueError("Список угловых точек должен содержать минимум 3 вершины")
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
