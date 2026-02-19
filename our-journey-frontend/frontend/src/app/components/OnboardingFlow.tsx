import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Progress } from './ui/progress';
import { useApp } from '../context/AppContext';
import { NC_COUNTIES } from '../data/nc-counties';
import { UserInfo, OnboardingStep } from '../types';

export const OnboardingFlow = () => {
  const navigate = useNavigate();
  const { setUserInfo, setOnboardingComplete, language } = useApp();
  const [step, setStep] = useState<number>(1);
  const [formData, setFormData] = useState<Partial<UserInfo>>({});

  const totalSteps = 5;
  const progress = (step / totalSteps) * 100;

  const handleNext = () => {
    if (step < totalSteps) {
      setStep(step + 1);
    } else {
      // Complete onboarding
      setUserInfo(formData as UserInfo);
      setOnboardingComplete(true);
      sessionStorage.setItem('onboardingCompleted', 'true');
      navigate('/chat');
    }
  };

  const handleSkip = () => {
    if (step < totalSteps) {
      // Skip to next step
      setStep(step + 1);
    } else {
      // Skip and complete onboarding
      setUserInfo(formData as UserInfo);
      setOnboardingComplete(true);
      sessionStorage.setItem('onboardingCompleted', 'true');
      navigate('/chat');
    }
  };

  const canProceed = () => {
    switch (step) {
      case 1:
        return formData.county !== undefined;
      case 2:
        return formData.releaseDate !== undefined;
      case 3:
        return formData.age18Plus !== undefined;
      default:
        return true;
    }
  };

  return (
    <div className="min-h-screen bg-[#F5F5F5] flex flex-col">
      {/* Header */}
      <div className="bg-white shadow-sm p-4">
        <div className="max-w-md mx-auto">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10">
              <img src="/Robin.png" alt="JoJo" className="w-full h-full object-contain" />
            </div>
            <div>
              <h2 className="font-semibold text-[#212121]">JoJo</h2>
              <p className="text-sm text-gray-500">
                {language === 'en' ? `Step ${step} of ${totalSteps}` : `Paso ${step} de ${totalSteps}`}
              </p>
            </div>
          </div>
          <Progress value={progress} className="h-2" />
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 p-6 overflow-y-auto">
        <div className="max-w-md mx-auto">
          <div className="bg-[#E8F5E9] rounded-2xl p-6 mb-6">
            {step === 1 && (
              <div>
                <p className="text-gray-800 mb-4">
                  {language === 'en'
                    ? 'What county in North Carolina are you in? This helps me find resources near you.'
                    : '¿En qué condado de Carolina del Norte te encuentras? Esto me ayuda a encontrar recursos cerca de ti.'}
                </p>
                <div className="space-y-2">
                  <Label htmlFor="county">
                    {language === 'en' ? 'Select County' : 'Seleccionar Condado'}
                  </Label>
                  <Select
                    value={formData.county}
                    onValueChange={(value) => setFormData({ ...formData, county: value })}
                  >
                    <SelectTrigger className="w-full bg-white">
                      <SelectValue placeholder={language === 'en' ? 'Choose a county...' : 'Elige un condado...'} />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="not-sure">
                        {language === 'en' ? "I'm not sure" : 'No estoy seguro/a'}
                      </SelectItem>
                      <SelectItem value="outside-nc">
                        {language === 'en' ? 'Outside NC' : 'Fuera de NC'}
                      </SelectItem>
                      {NC_COUNTIES.map(county => (
                        <SelectItem key={county} value={county}>
                          {county}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            )}

            {step === 2 && (
              <div>
                <p className="text-gray-800 mb-4">
                  {language === 'en'
                    ? 'When were you most recently released?'
                    : '¿Cuándo fuiste liberado/a más recientemente?'}
                </p>
                <div className="space-y-2">
                  {[
                    { value: 'less-30', label: language === 'en' ? 'Less than 30 days ago' : 'Hace menos de 30 días' },
                    { value: '1-6-months', label: language === 'en' ? '1-6 months ago' : 'Hace 1-6 meses' },
                    { value: '6-12-months', label: language === 'en' ? '6-12 months ago' : 'Hace 6-12 meses' },
                    { value: 'more-year', label: language === 'en' ? 'More than a year ago' : 'Hace más de un año' },
                    { value: 'not-yet', label: language === 'en' ? 'Not yet released (planning ahead)' : 'Aún no liberado/a (planificando)' }
                  ].map(option => (
                    <button
                      key={option.value}
                      onClick={() => setFormData({ ...formData, releaseDate: option.value })}
                      className={`w-full p-4 rounded-xl text-left transition-all ${
                        formData.releaseDate === option.value
                          ? 'bg-[#1B5E20] text-white'
                          : 'bg-white hover:bg-gray-50 text-gray-700 border border-gray-200'
                      }`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {step === 3 && (
              <div>
                <p className="text-gray-800 mb-4">
                  {language === 'en'
                    ? 'Are you 18 years or older?'
                    : '¿Tienes 18 años o más?'}
                </p>
                <div className="space-y-2">
                  <button
                    onClick={() => setFormData({ ...formData, age18Plus: true })}
                    className={`w-full p-4 rounded-xl text-left transition-all ${
                      formData.age18Plus === true
                        ? 'bg-[#1B5E20] text-white'
                        : 'bg-white hover:bg-gray-50 text-gray-700 border border-gray-200'
                    }`}
                  >
                    {language === 'en' ? 'Yes' : 'Sí'}
                  </button>
                  <button
                    onClick={() => setFormData({ ...formData, age18Plus: false })}
                    className={`w-full p-4 rounded-xl text-left transition-all ${
                      formData.age18Plus === false
                        ? 'bg-[#1B5E20] text-white'
                        : 'bg-white hover:bg-gray-50 text-gray-700 border border-gray-200'
                    }`}
                  >
                    {language === 'en' ? 'No' : 'No'}
                  </button>
                </div>
                {formData.age18Plus === false && (
                  <p className="mt-4 text-sm text-amber-700 bg-amber-50 p-3 rounded-lg">
                    {language === 'en'
                      ? "We'll connect you with resources specifically for minors."
                      : 'Te conectaremos con recursos específicamente para menores.'}
                  </p>
                )}
              </div>
            )}

            {step === 4 && (
              <div>
                <p className="text-gray-800 mb-4">
                  {language === 'en'
                    ? 'How do you identify? This helps me find the right resources for you.'
                    : '¿Cómo te identificas? Esto me ayuda a encontrar los recursos adecuados para ti.'}
                </p>
                <div className="space-y-2">
                  {[
                    { value: 'male', label: language === 'en' ? 'Male' : 'Masculino' },
                    { value: 'female', label: language === 'en' ? 'Female' : 'Femenino' },
                    { value: 'non-binary', label: language === 'en' ? 'Non-binary' : 'No binario' },
                    { value: 'prefer-not', label: language === 'en' ? 'Prefer not to say' : 'Prefiero no decir' }
                  ].map(option => (
                    <button
                      key={option.value}
                      onClick={() => setFormData({ ...formData, gender: option.value })}
                      className={`w-full p-4 rounded-xl text-left transition-all ${
                        formData.gender === option.value
                          ? 'bg-[#1B5E20] text-white'
                          : 'bg-white hover:bg-gray-50 text-gray-700 border border-gray-200'
                      }`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {step === 5 && (
              <div>
                <p className="text-gray-800 mb-4">
                  {language === 'en'
                    ? 'Would you like to share your contact info so we can follow up with additional support?'
                    : '¿Te gustaría compartir tu información de contacto para que podamos hacer seguimiento con apoyo adicional?'}
                </p>
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="email">
                      {language === 'en' ? 'Email (Optional)' : 'Correo electrónico (Opcional)'}
                    </Label>
                    <Input
                      id="email"
                      type="email"
                      placeholder={language === 'en' ? 'your@email.com' : 'tu@correo.com'}
                      value={formData.email || ''}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      className="mt-2 bg-white"
                    />
                  </div>
                  <div>
                    <Label htmlFor="phone">
                      {language === 'en' ? 'Phone (Optional)' : 'Teléfono (Opcional)'}
                    </Label>
                    <Input
                      id="phone"
                      type="tel"
                      placeholder={language === 'en' ? '(555) 123-4567' : '(555) 123-4567'}
                      value={formData.phone || ''}
                      onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                      className="mt-2 bg-white"
                    />
                  </div>
                  <p className="text-sm text-gray-600">
                    {language === 'en'
                      ? "We'll only use this to help you—never to spam."
                      : 'Solo usaremos esto para ayudarte, nunca para spam.'}
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="space-y-3">
            <Button
              onClick={handleNext}
              disabled={!canProceed()}
              className="w-full bg-[#1B5E20] hover:bg-[#388E3C] text-white py-6 rounded-xl disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              {step === totalSteps
                ? (language === 'en' ? 'Get Started' : 'Comenzar')
                : (language === 'en' ? 'Next' : 'Siguiente')}
            </Button>
            
            <Button
              onClick={handleSkip}
              variant="outline"
              className="w-full border-2 border-gray-300 py-6 rounded-xl hover:bg-gray-50"
            >
              {language === 'en' ? 'Skip' : 'Omitir'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};