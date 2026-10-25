import uuid
from pathlib import Path
from docx import Document
from docxtpl import DocxTemplate


class DocumentBuildError(Exception):
    pass


_deposit_names: dict[str, str] = {}

REQUIRED_CONTEXT_KEYS = (
    "fmt",
    "corner_points",
    "explanatory_note",
    "chemical_oxides",
    "extra_characteristics",
    "applications",
)


def build_passport(context: dict) -> str:
    for key in REQUIRED_CONTEXT_KEYS:
        if key not in context:
            raise DocumentBuildError(f"В контексте отсутствует обязательный ключ: {key}")
    if not isinstance(context["fmt"], dict):
        raise DocumentBuildError("Ключ 'fmt' должен быть словарем")

    try:
        template_path = Path(__file__).resolve().parent / "templates" / "passport_template.docx"
        output_dir = Path(__file__).resolve().parent / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        doc = DocxTemplate(str(template_path))
        doc.render(context)
        deposit_title = str(context.get("deposit_name", "")).strip()
        doc.docx.core_properties.title = deposit_title
        file_id = str(uuid.uuid4())
        _deposit_names[file_id] = deposit_title
        out_path = output_dir / f"{file_id}.docx"
        doc.save(str(out_path))
        return file_id
    except Exception as exc:
        raise DocumentBuildError(f"Ошибка при создании документа: {exc}") from exc


def resolve_passport_path(file_id: str) -> Path | None:
    try:
        parsed_uuid = uuid.UUID(file_id)
    except (ValueError, TypeError, AttributeError):
        return None
    base_dir = (Path(__file__).resolve().parent / "output").resolve()
    target_path = (base_dir / f"{parsed_uuid}.docx").resolve()
    if not target_path.is_relative_to(base_dir):
        return None
    if not target_path.is_file():
        return None
    return target_path


def get_deposit_name(file_id: str) -> str | None:
    if file_id in _deposit_names:
        return _deposit_names[file_id]
    path = resolve_passport_path(file_id)
    if path is not None and path.is_file():
        try:
            d = Document(str(path))
            title = d.core_properties.title
            if title:
                _deposit_names[file_id] = title
                return title
        except Exception:
            return None
    return None
