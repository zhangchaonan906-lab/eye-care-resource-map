import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CorrectionReportForm } from "./correction-report-form";

afterEach(() => vi.unstubAllGlobals());

describe("CorrectionReportForm", () => {
  it("submits a report for manual review and tells the user data is not changed directly", async () => {
    const fetchMock = vi.fn(async () => Response.json({ data: { status: "pending" } }, { status: 202 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<CorrectionReportForm facilityId="00000000-0000-4000-8000-000000000001" />);
    fireEvent.click(screen.getByText("报告机构信息问题"));
    fireEvent.change(screen.getByLabelText("说明"), { target: { value: "该机构已迁至新地址，请核实。" } });
    fireEvent.click(screen.getByRole("button", { name: "提交审核" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/corrections", expect.objectContaining({ method: "POST" })));
    expect(await screen.findByText("已提交，内容将由工作人员审核；不会自动修改机构信息。"))
      .toBeInTheDocument();
  });
});
