import React, { useState } from "react";
import { LogOut, RotateCcw, Star } from "lucide-react";

type Props = {
  bookingId: string;
  isSubmitting: boolean;
  onSubmit: (rating: number, comment?: string) => Promise<boolean>;
  onExit: () => Promise<void>;
  onContinue: () => Promise<void>;
};

export const PostBookingRatingDialog: React.FC<Props> = ({
  bookingId,
  isSubmitting,
  onSubmit,
  onExit,
  onContinue,
}) => {
  const [rating, setRating] = useState(0);
  const [hovered, setHovered] = useState(0);
  const [comment, setComment] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const submit = async () => {
    if (rating === 0 || isSubmitting) return;
    if (await onSubmit(rating, comment)) setSubmitted(true);
  };

  return (
    <div className="absolute inset-0 z-30 grid place-items-center rounded-3xl bg-slate-950/55 p-4" role="dialog" aria-modal="true" aria-labelledby="post-booking-rating-title">
      <div className="w-full max-w-md rounded-3xl bg-white p-6 shadow-2xl dark:bg-slate-900">
        <h3 id="post-booking-rating-title" className="text-lg font-bold text-slate-900 dark:text-white">
          Đánh giá chất lượng dịch vụ
        </h3>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Chuyến xe <span className="font-mono font-semibold">{bookingId}</span>
        </p>

        <div className="mt-5 flex justify-center gap-1" role="group" aria-label="Đánh giá từ một đến năm sao">
          {[1, 2, 3, 4, 5].map((value) => (
            <button
              key={value}
              type="button"
              disabled={submitted || isSubmitting}
              onMouseEnter={() => setHovered(value)}
              onMouseLeave={() => setHovered(0)}
              onClick={() => setRating(value)}
              className="rounded-lg p-1 transition hover:bg-amber-50 disabled:opacity-60 dark:hover:bg-white/5"
              aria-label={`${value} sao`}
            >
              <Star
                className={`h-8 w-8 ${
                  value <= (hovered || rating)
                    ? "fill-amber-400 text-amber-400"
                    : "text-slate-300 dark:text-slate-600"
                }`}
              />
            </button>
          ))}
        </div>

        {submitted ? (
          <p className="mt-4 rounded-xl bg-emerald-50 px-3 py-2 text-center text-sm font-medium text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300">
            Cảm ơn bạn đã gửi đánh giá!
          </p>
        ) : (
          <>
            <textarea
              value={comment}
              onChange={(event) => setComment(event.target.value)}
              maxLength={500}
              rows={3}
              placeholder="Ý kiến về chất lượng dịch vụ (không bắt buộc)"
              className="mt-4 w-full resize-none rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-700 outline-none focus:border-[#00A99D] dark:border-white/10 dark:bg-white/5 dark:text-white"
            />
            <button
              type="button"
              onClick={() => void submit()}
              disabled={rating === 0 || isSubmitting}
              className="mt-3 w-full rounded-xl bg-[#00A99D] px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
            >
              {isSubmitting ? "Đang gửi…" : "Gửi đánh giá"}
            </button>
          </>
        )}

        <div className="mt-5 grid grid-cols-1 gap-2 sm:grid-cols-2">
          <button
            type="button"
            onClick={() => void onContinue()}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white dark:bg-white dark:text-slate-900"
          >
            <RotateCcw className="h-4 w-4" />
            Tiếp tục đặt xe
          </button>
          <button
            type="button"
            onClick={() => void onExit()}
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 dark:border-white/20 dark:text-white"
          >
            <LogOut className="h-4 w-4" />
            Thoát
          </button>
        </div>
      </div>
    </div>
  );
};
