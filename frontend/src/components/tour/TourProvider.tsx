import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';

import { TourDoneDialog, TourWelcomeDialog } from './TourDialogs';
import { resolveTourRoute } from './tourRoutes';
import { TourSpotlight } from './TourSpotlight';
import { TOUR_STEPS, type TourScreen } from './tourSteps';

const SEEN_KEY = 'autoform.tour-seen';

type Phase = 'idle' | 'welcome' | 'step' | 'done';

interface TourContextValue {
  phase: Phase;
  start: () => void;
}

const TourContext = createContext<TourContextValue | null>(null);

export function TourProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const [phase, setPhase] = useState<Phase>('idle');
  const [index, setIndex] = useState(0);
  const [moving, setMoving] = useState(false);
  const screenRef = useRef<TourScreen | null>(null);

  useEffect(() => {
    if (!localStorage.getItem(SEEN_KEY)) setPhase('welcome');
  }, []);

  const finish = useCallback((next: Phase) => {
    localStorage.setItem(SEEN_KEY, '1');
    setPhase(next);
    screenRef.current = null;
  }, []);

  const goTo = useCallback(async (target: number) => {
    const step = TOUR_STEPS[target];
    if (!step) return finish('done');
    if (screenRef.current !== step.screen) {
      setMoving(true);
      try {
        navigate(await resolveTourRoute(step.screen));
        screenRef.current = step.screen;
      } catch {
        // Không mở được màn hình (VD backend chưa sẵn sàng): vẫn hiện bước ở màn hình hiện tại
      } finally {
        setMoving(false);
      }
    }
    setIndex(target);
    setPhase('step');
  }, [finish, navigate]);

  const value = useMemo<TourContextValue>(() => ({
    phase,
    start: () => {
      screenRef.current = null;
      void goTo(0);
    },
  }), [goTo, phase]);

  const step = TOUR_STEPS[index];
  return (
    <TourContext.Provider value={value}>
      {children}
      <TourWelcomeDialog open={phase === 'welcome'} total={TOUR_STEPS.length} onStart={() => void goTo(0)} onLater={() => finish('idle')} />
      {phase === 'step' && step && !moving && (
        <TourSpotlight
          key={index}
          step={step}
          index={index}
          total={TOUR_STEPS.length}
          onNext={() => void goTo(index + 1)}
          onBack={() => void goTo(Math.max(0, index - 1))}
          onSkip={() => finish('idle')}
        />
      )}
      <TourDoneDialog open={phase === 'done'} onRestart={value.start} onClose={() => { setPhase('idle'); navigate('/'); }} />
    </TourContext.Provider>
  );
}

export function useTour(): TourContextValue {
  const value = useContext(TourContext);
  if (!value) throw new Error('useTour phải nằm trong <TourProvider>');
  return value;
}
