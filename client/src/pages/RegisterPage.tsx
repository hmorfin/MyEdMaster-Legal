import { RegisterForm } from "@/components/RegisterForm"
import AuthImage from '@/assets/images/AuthImage.png'
import metyMainLogo from "@/assets/images/Mety Main Logo.png"
import metyMainWhiteLogo from "@/assets/images/Mety Main Logo White.png"

export default function RegisterPage() {
  return (
    <div className="grid min-h-svh lg:grid-cols-2">
      <div className="flex flex-col gap-4 p-6 md:p-10">
        <div className="flex justify-center gap-2 md:justify-start">
          <a href="/" className="flex items-center">
            <img src={metyMainLogo} alt="Mety" className="h-4.5 w-auto object-contain dark:hidden" />
            <img src={metyMainWhiteLogo} alt="Mety" className="hidden h-4.5 w-auto object-contain dark:block" />
          </a>
        </div>
        <div className="flex flex-1 items-center justify-center">
          <div className="w-full max-w-xs">
            <RegisterForm />
          </div>
        </div>
      </div>
      <div className="bg-muted relative hidden lg:block">
        <img
          src={AuthImage}
          alt="Image"
          className="absolute inset-0 h-full w-full object-cover"
        />
      </div>
    </div>
  )
}
