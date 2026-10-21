export class ApiError extends Error {
  status: number;
  detail: string | null;
  retryAfter: number | null;
  requestId: string | null;

  constructor(
    status: number,
    message: string,
    opts: { detail?: string | null; retryAfter?: number | null; requestId?: string | null } = {},
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = opts.detail ?? null;
    this.retryAfter = opts.retryAfter ?? null;
    this.requestId = opts.requestId ?? null;
  }

  /** 재시도해 볼 만한 오류인지: 네트워크(0)·요청 과다(429)·서버 오류(5xx)만 해당 */
  get retryable(): boolean {
    return this.status === 0 || this.status === 429 || this.status >= 500;
  }

  static async fromResponse(res: Response): Promise<ApiError> {
    let detail: string | null = null;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* 본문이 JSON이 아니면 상태 코드로 안내 */
    }
    const retryHeader = Number(res.headers.get("Retry-After"));
    const retryAfter = Number.isFinite(retryHeader) && retryHeader > 0 ? retryHeader : null;
    return new ApiError(res.status, messageFor(res.status, detail, retryAfter), {
      detail,
      retryAfter,
      requestId: res.headers.get("X-Request-ID"),
    });
  }
}

function messageFor(status: number, detail: string | null, retryAfter: number | null): string {
  if (status === 429) {
    return retryAfter
      ? `요청이 너무 많습니다. ${retryAfter}초 후 다시 시도해 주세요.`
      : "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.";
  }
  if (status === 403) return detail ?? "권한이 없습니다.";
  if (status === 404) return detail ?? "요청한 정보를 찾을 수 없습니다.";
  if (status >= 500) return detail ?? "서버에 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.";
  return detail ?? `요청에 실패했습니다 (${status}).`;
}

/** 어떤 예외든 사용자에게 보여줄 한국어 문구로 바꾼다. */
export function describeError(err: unknown, fallback = "데이터를 불러오지 못했습니다."): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof Error && err.message) return err.message;
  return fallback;
}
