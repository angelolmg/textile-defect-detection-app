import { Injectable } from '@angular/core';
import { CanDeactivate } from '@angular/router';
import { PatchingComponent } from './pages/patching/patching.component';

@Injectable({
  providedIn: 'root'
})
export class UnsavedChangesGuard implements CanDeactivate<PatchingComponent> {
  canDeactivate(component: PatchingComponent): boolean {
    return component.canDeactivate() ? true : confirm('You have unsaved changes! Do you really want to leave?');
  }
}
