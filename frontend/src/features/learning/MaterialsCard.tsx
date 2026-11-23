import { useEffect, useRef, useState, type ChangeEvent } from "react"
import {
  CheckCircle2,
  CircleAlert,
  FileText,
  LoaderCircle,
  RefreshCw,
  Trash2,
  Upload,
} from "lucide-react"
import { api } from "../../api"
import type { DailyLearningMaterial } from "../../api/types"
import Button from "../../components/ui/Button"
import Card from "../../components/ui/Card"
import Modal from "../../components/ui/Modal"
import {
  MAX_SELECTED_MATERIALS,
  POLL_INTERVAL_MS,
  formatBytes,
  formatMaterialError,
  learningError,
  materialMime,
  materialStatus,
  readFileBase64,
  validateMaterialFile,
} from "./learningApi"

type UploadAttempt = {
  file: File
  key: string
}

export default function MaterialsCard({
  onSelectionChange,
  onMaterialsChange,
}: {
  onSelectionChange: (materials: DailyLearningMaterial[]) => void
  onMaterialsChange: (materials: DailyLearningMaterial[]) => void
}) {
  const [materials, setMaterials] = useState<DailyLearningMaterial[]>([])
  const [selected, setSelected] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState("")
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [deleteTarget, setDeleteTarget] =
    useState<DailyLearningMaterial | null>(null)
  const uploadRef = useRef<HTMLInputElement>(null)
  const uploadAttempt = useRef<UploadAttempt | null>(null)
  const deleteKey = useRef("")

  async function load() {
    setError("")
    try {
      setMaterials(await api.listLearningMaterials())
    } catch (cause) {
      setError(learningError(cause))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  useEffect(() => {
    const valid = selected.filter((id) =>
      materials.some(
        (material) =>
          material.material_id === id && material.status === "READY",
      ),
    )
    if (valid.length !== selected.length) setSelected(valid)
    onSelectionChange(
      valid.flatMap((id) => {
        const material = materials.find((item) => item.material_id === id)
        return material ? [material] : []
      }),
    )
  }, [materials, selected, onSelectionChange])

  useEffect(() => onMaterialsChange(materials), [materials, onMaterialsChange])

  useEffect(() => {
    const pending = materials.filter(
      (material) => materialStatus(material.status).polling,
    )
    if (!pending.length) return
    let active = true
    const timer = window.setTimeout(() => {
      void Promise.all(
        pending.map((material) =>
          api.getLearningMaterial(material.material_id).catch(() => material),
        ),
      ).then((next) => {
        if (!active) return
        const byId = new Map(next.map((item) => [item.material_id, item]))
        setMaterials((current) =>
          current.map((item) => byId.get(item.material_id) ?? item),
        )
      })
    }, POLL_INTERVAL_MS)
    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [materials])

  async function upload(file: File, retry = false) {
    const validation = validateMaterialFile(file)
    if (validation) {
      setError(validation)
      return
    }
    const mime = materialMime(file)
    if (!mime) return
    if (!retry || !uploadAttempt.current)
      uploadAttempt.current = { file, key: crypto.randomUUID() }
    setBusy("upload")
    setError("")
    setNotice("")
    try {
      const material = await api.uploadLearningMaterial(
        file.name,
        mime,
        await readFileBase64(file),
        null,
        uploadAttempt.current.key,
      )
      setMaterials((current) => [
        material,
        ...current.filter((item) => item.material_id !== material.material_id),
      ])
      setNotice("Máy chủ đã nhận tệp và đang xử lý trạng thái lập chỉ mục.")
      uploadAttempt.current = null
    } catch (cause) {
      setError(learningError(cause))
    } finally {
      setBusy("")
    }
  }

  function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ""
    if (file) void upload(file)
  }

  function toggle(material: DailyLearningMaterial) {
    if (material.status !== "READY") return
    setSelected((current) => {
      if (current.includes(material.material_id))
        return current.filter((id) => id !== material.material_id)
      if (current.length >= MAX_SELECTED_MATERIALS) {
        setError("Mỗi phiên học chỉ được chọn tối đa 5 tài liệu.")
        return current
      }
      setError("")
      return [...current, material.material_id]
    })
  }

  async function remove() {
    if (!deleteTarget || busy) return
    if (!deleteKey.current) deleteKey.current = crypto.randomUUID()
    setBusy("delete")
    setError("")
    try {
      await api.deleteLearningMaterial(
        deleteTarget.material_id,
        deleteKey.current,
      )
      setMaterials((current) =>
        current.filter((item) => item.material_id !== deleteTarget.material_id),
      )
      setSelected((current) =>
        current.filter((id) => id !== deleteTarget.material_id),
      )
      setDeleteTarget(null)
      deleteKey.current = ""
      setNotice("Đã xoá tài liệu theo xác nhận của máy chủ.")
    } catch (cause) {
      setError(learningError(cause))
    } finally {
      setBusy("")
    }
  }

  return (
    <>
      <input
        ref={uploadRef}
        className="hidden"
        type="file"
        accept=".pdf,.txt,.md,application/pdf,text/plain,text/markdown"
        onChange={chooseFile}
      />
      <Card
        className="study-card learning-materials-card"
        title="Tài liệu của bạn"
        action={
          <Button
            className="primary learning-compact-action"
            disabled={Boolean(busy)}
            onClick={() => uploadRef.current?.click()}
          >
            <Upload size={15} aria-hidden="true" />
            Thêm tài liệu
          </Button>
        }
      >
        <div className="learning-card-body">
          <div className="learning-card-intro">
            <p>Nguồn được chọn sẽ giới hạn phạm vi trả lời của trợ lý.</p>
            <Button
              className="icon-button learning-refresh"
              aria-label="Tải lại danh sách tài liệu"
              title="Tải lại"
              disabled={loading || Boolean(busy)}
              onClick={() => {
                setLoading(true)
                void load()
              }}
            >
              <RefreshCw size={15} aria-hidden="true" />
            </Button>
          </div>
          {(error || notice) && (
            <div
              className={`learning-inline-message ${
                error ? "is-error" : "is-success"
              }`}
              role={error ? "alert" : "status"}
            >
              {error ? (
                <CircleAlert size={16} aria-hidden="true" />
              ) : (
                <CheckCircle2 size={16} aria-hidden="true" />
              )}
              <span>{error || notice}</span>
              {error && uploadAttempt.current && (
                <button
                  type="button"
                  onClick={() => void upload(uploadAttempt.current!.file, true)}
                >
                  Thử lại
                </button>
              )}
            </div>
          )}
          {loading ? (
            <div className="learning-state" role="status">
              <LoaderCircle className="learning-spin" aria-hidden="true" />
              Đang tải tài liệu…
            </div>
          ) : materials.length ? (
            <ul className="learning-material-list">
              {materials.map((material) => {
                const status = materialStatus(material.status)
                const checked = selected.includes(material.material_id)
                return (
                  <li key={material.material_id}>
                    <label
                      className={
                        material.status !== "READY" ? "is-disabled" : ""
                      }
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        disabled={material.status !== "READY"}
                        onChange={() => toggle(material)}
                      />
                      <span className="learning-file-icon">
                        <FileText size={17} aria-hidden="true" />
                      </span>
                      <span className="learning-file-copy">
                        <strong title={material.filename}>
                          {material.filename}
                        </strong>
                        <span>
                          {formatBytes(material.byte_size)}
                          {material.page_count
                            ? ` · ${material.page_count} trang`
                            : ""}
                        </span>
                        {material.status === "FAILED" && (
                          <small>{formatMaterialError(material)}</small>
                        )}
                      </span>
                    </label>
                    <span
                      className={`learning-status is-${status.tone}`}
                      role="status"
                    >
                      {status.polling && (
                        <LoaderCircle
                          className="learning-spin"
                          size={13}
                          aria-hidden="true"
                        />
                      )}
                      {status.label}
                    </span>
                    <Button
                      className="icon-button learning-delete"
                      aria-label={`Xoá tài liệu ${material.filename}`}
                      disabled={Boolean(busy)}
                      onClick={() => {
                        deleteKey.current = ""
                        setDeleteTarget(material)
                      }}
                    >
                      <Trash2 size={15} aria-hidden="true" />
                    </Button>
                  </li>
                )
              })}
            </ul>
          ) : (
            <div className="learning-state is-empty learning-material-empty">
              <span className="learning-empty-icon">
                <FileText aria-hidden="true" />
              </span>
              <strong>Thêm tài liệu để bắt đầu</strong>
              <span>
                PDF, TXT hoặc Markdown tối đa 5 MiB và 50 trang. Tài liệu phải ở
                trạng thái sẵn sàng mới có thể chọn.
              </span>
              <Button
                className="secondary"
                disabled={Boolean(busy)}
                onClick={() => uploadRef.current?.click()}
              >
                <Upload size={16} aria-hidden="true" />
                Chọn tài liệu
              </Button>
            </div>
          )}
          <p className="learning-selection-count" role="status">
            <strong>
              Đã chọn {selected.length}/{MAX_SELECTED_MATERIALS} tài liệu
            </strong>
            <span> · Chỉ tài liệu READY</span>
          </p>
        </div>
      </Card>
      {deleteTarget && (
        <Modal title="Xoá tài liệu?" close={() => setDeleteTarget(null)}>
          <div className="learning-modal-copy">
            <p>
              Bạn sắp xoá <strong>{deleteTarget.filename}</strong>. Lịch sử
              trích dẫn vẫn được giữ dưới nhãn “Tài liệu đã xoá”.
            </p>
            <div className="learning-modal-actions">
              <Button
                className="secondary"
                disabled={Boolean(busy)}
                onClick={() => setDeleteTarget(null)}
              >
                Huỷ
              </Button>
              <Button
                className="danger"
                disabled={Boolean(busy)}
                onClick={() => void remove()}
              >
                {busy === "delete" ? "Đang xoá…" : "Xác nhận xoá"}
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </>
  )
}
