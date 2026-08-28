import { XCircle } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { crashComponentPropsType } from "../../../types/components";
import { Button } from "../../ui/button";
import { Card, CardFooter, CardHeader } from "../../ui/card";

export default function CrashErrorComponent({
  error,
  resetErrorBoundary,
}: crashComponentPropsType): JSX.Element {
  const { t } = useTranslation();
  return (
    <div className="z-50 flex h-screen w-screen items-center justify-center bg-foreground bg-opacity-50">
      <div className="flex h-screen w-screen flex-col bg-background text-start shadow-lg">
        <main className="m-auto grid w-1/2 justify-center gap-5 text-center">
          <Card className="p-8" role="alert">
            <CardHeader>
              <div className="m-auto">
                <XCircle
                  strokeWidth={1.5}
                  className="h-16 w-16"
                  aria-hidden="true"
                />
              </div>
              <div>
                <h1 className="mb-4 text-xl text-foreground">
                  {t("crash.title")}
                </h1>
              </div>
            </CardHeader>

            <CardFooter>
              <div className="m-auto mt-4 flex justify-center">
                <Button onClick={resetErrorBoundary}>
                  {t("crash.restartButton")}
                </Button>
              </div>
            </CardFooter>
          </Card>
        </main>
      </div>
    </div>
  );
}
